import hashlib, json, os, re, sys, time
sys.path.insert(0, "/tmp")
import bridge_client as bc

# Queue worker id on the server; this process runs one slot (SLOT_ID and session nonce from the environment).
POOL_ID = bc.WORKER_ID
bc.WORKER_ID = os.environ["SLOT_ID"]
bc.CONTEXT_SESSION = os.environ["SLOT_NONCE"]
MAX = max(1, int(re.sub(r"\D", "", os.environ.get("SLOT_MAX", "")) or 10))
# Time budget: after about 4 minutes a slot finishes the task in hand and stops (a round waits for its slowest).
SECONDS = max(1, int(re.sub(r"\D", "", os.environ.get("SLOT_SECONDS", "")) or 240))
# One lease/chunk/state file PER SLOT (slots run in parallel). /tmp is shared, so a task's files are deleted
# as soon as its answer is stored.
bc.LEASES = "/tmp/bridge_leases_" + bc.WORKER_ID + ".json"
bc.CHUNKS = "/tmp/bridge_chunks_" + bc.WORKER_ID + ".json"
bc.CLEANUP = True
# Notes in outputs name this helper's own commands (page, ctx, search) instead of Python calls.
bc.SHELL = "python3 /tmp/bridge_slot.py"
STATE = "/tmp/bridge_state_" + bc.WORKER_ID + ".json"
ME = hashlib.sha256(bc.CONTEXT_SESSION.encode("utf-8")).hexdigest()[:16]
ENDS = ("session_should_end", "session_exhausted", "session_retired", "slot_done")

def _state(fresh=False):
    s = {} if fresh else bc._load(STATE)
    if s.get("me") != ME:  # new slot session (new nonce): reset counters
        s = {"me": ME, "started": time.time(), "answers": 0, "idle": 0, "errors": 0}
        bc._save(STATE, s)
    return s

def _over(s):
    return s["answers"] >= MAX or time.time() - s["started"] >= SECONDS

def _report(out, s):
    # Add "answers" and "slot_done" (true = stop now and reply "done N"). Never done while a task is in hand.
    status = out.get("next_status") or out.get("status")
    s["idle"] = s["idle"] + 1 if status == "timeout" else 0
    s["errors"] = s["errors"] + 1 if "error" in out else 0
    bc._save(STATE, s)
    if "error" in out:
        done = s["errors"] >= 3
    else:
        idle = status == "timeout" and (s["answers"] > 0 or s["idle"] >= 2)
        done = status != "task" and (_over(s) or idle or status in ENDS)
    out["answers"], out["slot_done"] = s["answers"], done
    return out

def register():
    _state(fresh=True)
    base = {"worker_id": bc.WORKER_ID, "context_session": bc.CONTEXT_SESSION, "context_fresh": True,
            "agent_turn": {"runtime": "chat.z.ai", "model": "GLM-5.3-Flash"}}
    try:
        bc.mcp_init()
        r = bc.call("worker_register", ephemeral=True, pool_id=POOL_ID, **base)
        if "error" in r and re.search("ephemeral|pool_id", json.dumps(r["error"])):
            r = bc.call("worker_register", **base)  # an older server without pool mode: a plain fresh session
    except Exception as e:
        return {"registered": False, "error": str(e)[:300]}
    session = r.get("context_session") or {}
    return {"registered": "error" not in r, "ephemeral": session.get("ephemeral", False), "error": r.get("error")}

def take():
    s = _state()
    if _over(s):
        return _report({"status": "slot_done"}, s)
    return _report(bc.take(), s)

def _answer(send):
    # Publish one answer. The LAST one (MAX reached or time up) does not wait for a next task.
    s = _state()
    out = send(s["answers"] + 1 >= MAX or time.time() - s["started"] >= SECONDS)
    if "error" not in out and not out.get("duplicate"):
        s["answers"] += 1
    return _report(out, s)

def toolcall(task_id, path, last):
    # Call the client's function instead of answering: the file holds {"tool_calls": [...]}.
    with open(path, encoding="utf-8") as f:
        structured = json.load(f)
    out = bc.publish(task_id, content="", structured=structured, last=last)
    bc._stored(task_id, out, [path])
    return out

def fail(task_id, code, message):
    # This task cannot be answered: report it (it is not retried), then take the next one.
    out = bc.call("report_task_error", **bc.lease(task_id), code=code, message=message, retryable=False, side_effects="none")
    bc._stored(task_id, out)
    return _report(out, _state())

def main(argv):
    rest, opts = bc._args(argv)
    cmd, n = (rest[0] if rest else ""), len(rest)
    note = {"public_note": opts["note"]} if opts.get("note") else {}
    last = opts.get("last", False) or cmd == "publish_last"
    if cmd == "register" and n == 1:
        return register()
    if cmd == "take" and n == 1:
        return take()
    if cmd == "chunk" and n == 3:
        return bc.chunk(rest[1], rest[2], channel=opts.get("channel", "answer"), **note)
    if cmd in ("publish", "publish_last") and n == 3:
        return _answer(lambda auto: bc.publish(rest[1], rest[2], last=last or auto, **note))
    if cmd == "finish" and n == 2:
        return _answer(lambda auto: bc.finish(rest[1], last=last or auto, **note))
    if cmd == "toolcall" and n == 3:
        return _answer(lambda auto: toolcall(rest[1], rest[2], last or auto))
    if cmd == "fail" and n == 4:
        return fail(rest[1], rest[2], rest[3])
    if cmd in ("page", "ctx", "search") and 3 <= n <= 5:
        # page TASK_ID K [PART [SIZE]] | ctx TASK_ID SEL [K] | search TASK_ID QUERY [MAX_HITS [K]]: read the saved task.
        return bc._cli(rest)
    if cmd == "images" and n == 2:
        # images TASK_ID: download the images of the task (those not saved yet) and list their files.
        return bc._cli(rest)
    return None

if __name__ == "__main__":
    try:
        result = main(sys.argv[1:])
    except Exception as e:  # network or protocol failure: show it as an error the worker can read
        s = _state()
        s["errors"] += 1
        bc._save(STATE, s)
        result = {"error": {"code": "helper_failed", "message": str(e)[:300]}, "answers": s["answers"], "slot_done": s["errors"] >= 3}
    # A result that holds a task (or a page of one) is printed as pages, everything else as one JSON line.
    print(result if isinstance(result, (str, bc.Paged)) else json.dumps(result, ensure_ascii=False) if result is not None else
          "usage: bridge_slot.py register | take | publish TASK_ID FILE | chunk TASK_ID FILE [--channel reasoning] | finish TASK_ID | toolcall TASK_ID FILE | fail TASK_ID CODE MESSAGE | page TASK_ID K [PART [SIZE]] | ctx TASK_ID SEL [K] | search TASK_ID QUERY [MAX_HITS [K]] | images TASK_ID")
