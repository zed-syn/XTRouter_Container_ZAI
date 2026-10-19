import hashlib, http.client, json, itertools, os, random, re, sys, time, unicodedata, urllib.error, urllib.request

MCP_URL = "https://board-mercy-external-shannon.trycloudflare.com/mcp"
WORKER_TOKENS = {
    "glm-pool-1": "lab_worker_yyICSJ2zayNXYF-ID8iR3YkfLuTRYZoG3QnOqKsDGTs",
    "glm-pool-2": "lab_worker_yyICSJ2zayNXYF-ID8iR3YkfLuTRYZoG3QnOqKsDGTs",
    "glm-pool-3": "lab_worker_yyICSJ2zayNXYF-ID8iR3YkfLuTRYZoG3QnOqKsDGTs",
}
_DEFAULT_WORKER_ID = "glm-pool-1"
_DEFAULT_CONTEXT_SESSION = "LVyC11F_93jWXDEtIQj0mcnREtwBw-y4"
_wid = os.environ.get("WORKER_ID", _DEFAULT_WORKER_ID).strip()
if _wid not in WORKER_TOKENS:
    sys.exit("WORKER_ID must be one of: " + ", ".join(sorted(WORKER_TOKENS)))
WORKER_ID = _wid
TOKEN = WORKER_TOKENS[WORKER_ID]
_ctx = os.environ.get("CONTEXT_SESSION", "").strip()
CONTEXT_SESSION = _ctx if _ctx else _DEFAULT_CONTEXT_SESSION
# Identifies THIS chat to the server (a new value is generated for every new chat).
LEASES = "/tmp/bridge_leases.json"
CHUNKS = "/tmp/bridge_chunks.json"
# Each task you receive is saved whole in its own file: TASKS + worker id + "@" + task_id + ".json". How many of its
# characters were printed for you is counted in ".reads" and sent with its answer or error (read_chars): never by hand.
TASKS = "/tmp/bridge_task_"
# The most one output may show: PRINT_CAP characters and PRINT_BYTES UTF-8 bytes, whichever is smaller (longer outputs
# are not shown whole). A conversation is shown as a WINDOW (its newest part + an index of the rest, fetched with ctx()
# and ctx_search()); other long tasks are shown in pages (page()).
PRINT_CAP = 24000
PRINT_BYTES = 24000
# Notes name helper commands as Python calls; the pool sub-agent helper sets SHELL to name its shell commands instead.
SHELL = ""
# True = once a task's answer is stored, delete its files and forget its lease (pool sub-agents share /tmp).
CLEANUP = False
# take() and publish() wait for a task up to WAIT_SECONDS inside ONE execution, as a chain of long-polls of at most
# POLL_SECONDS each, and return as soon as a task arrives. Nothing the helper does in one execution runs longer than
# EXEC_SECONDS in total (the sandbox stops an execution at 120 s).
WAIT_SECONDS = 105
POLL_SECONDS = 50
EXEC_SECONDS = 110
# A call the server could not answer (restart, tunnel hiccup: connection refused/reset/timeout, HTTP 502/503/504) is
# sent again with growing pauses for up to RETRY_SECONDS, never past EXEC_SECONDS. Safe: the server de-duplicates it.
RETRY_SECONDS = 90
# The images of a task are saved, under neutral names (image-1.png ...), in IMAGE_FOLDER of the first of IMAGE_HOMES that
# exists, one sub-folder per task; each one is fetched in parts of at most FILE_CHUNK bytes and checked against its sha256.
IMAGE_HOMES = ("/home/z/my-project", "/tmp")
IMAGE_FOLDER = "uploads"
FILE_CHUNK = 4000000
_EXTENSIONS = {"image/png": "png", "image/jpeg": "jpg", "image/gif": "gif", "image/webp": "webp"}
_FORMATS = {"image/png": "PNG", "image/jpeg": "JPEG", "image/gif": "GIF", "image/webp": "WebP"}
_ids = itertools.count(1)
_NL, _BS = chr(10), chr(92)
_SYS = ("system", "developer")
# [start, last activity] of the current execution: helper calls less than 2 s apart belong to the same execution.
_exec = [0.0, -1e9]

def _execution():
    now = time.monotonic()
    if now - _exec[1] > 2:
        _exec[0] = now
    _exec[1] = now
    return _exec[0]

def _post(payload, timeout=90):
    data = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json", "Accept": "application/json",
               "Authorization": "Bearer " + TOKEN, "User-Agent": "glm-web-worker/1.0"}
    end, delay, retry_end = _execution() + EXEC_SECONDS, 1.0, None
    try:
        while True:
            left = end - time.monotonic()
            if left < 1:
                raise TimeoutError("no time left in this execution: run the command again")
            try:
                req = urllib.request.Request(MCP_URL, data=data, method="POST", headers=headers)
                with urllib.request.urlopen(req, timeout=min(timeout, left)) as resp:
                    body = resp.read().decode("utf-8")
                    return json.loads(body) if body else None
            except urllib.error.HTTPError as e:
                if e.code not in (502, 503, 504):
                    raise  # any other HTTP error (4xx, 500) is an answer from the server: never repeated
                failure = e
            except (OSError, http.client.HTTPException) as e:
                failure = e  # connection refused / reset / timeout / dropped mid-response
            now = time.monotonic()
            retry_end = now + RETRY_SECONDS if retry_end is None else retry_end
            wait = min(delay, 15.0) * random.uniform(0.5, 1.0)
            if now + wait + 1 > min(retry_end, end):
                raise failure
            time.sleep(wait)
            delay *= 2
    finally:
        _exec[1] = time.monotonic()

def mcp_init():
    _post({"jsonrpc": "2.0", "id": next(_ids), "method": "initialize",
           "params": {"protocolVersion": "2025-03-26", "capabilities": {},
                      "clientInfo": {"name": "glm-web-worker", "version": "1.0"}}})
    _post({"jsonrpc": "2.0", "method": "notifications/initialized"})

def _rejected(args, error):
    # The optional argument (public_note, read_chars) that the server refused, named in its error; None otherwise.
    text = json.dumps(error)
    return next((k for k in ("public_note", "read_chars") if k in args and k in text), None)

def call(tool, **args):
    return _call(tool, _with_reads(tool, args))

def _call(tool, args, timeout=90):
    res = _post({"jsonrpc": "2.0", "id": next(_ids), "method": "tools/call",
                 "params": {"name": tool, "arguments": args}}, timeout)
    if "error" in res:
        name = _rejected(args, res["error"])
        if name:
            args.pop(name)
            return _call(tool, args, timeout)
        raise RuntimeError(res["error"])
    out = json.loads(res["result"]["content"][0]["text"])
    err = out.get("error") if isinstance(out, dict) else None
    name = _rejected(args, err) if isinstance(err, dict) and err.get("code") == "invalid_argument" else None
    if name:
        # The server did not accept this optional argument (nothing ran): send the same call again without it.
        args.pop(name)
        return _call(tool, args, timeout)
    return out

def _load(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}

def _save(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)

def _drop(path):
    try:
        os.remove(path)
    except OSError:
        pass

def _task_file(task_id):
    return TASKS + WORKER_ID + "@" + task_id + ".json"

def _reads_file(task_id):
    return TASKS + WORKER_ID + "@" + task_id + ".reads"

def _safe_id(task_id):
    # A task id usable in a file name (letters, digits, "_.:-"), or "" for anything else.
    task_id = str(task_id or "")
    return task_id if task_id and all(c.isalnum() or c in "_.:-" for c in task_id) else ""

def _counted(task_id, text):
    # Count the characters of a task printed for you (first read, page, ctx, ctx_search): one line per output, appended,
    # so outputs printed by parallel executions never overwrite each other. Error texts (no "[[" marker) do not count.
    if _safe_id(task_id) and text.startswith("[["):
        try:
            with open(_reads_file(_safe_id(task_id)), "a", encoding="utf-8") as f:
                f.write("%d%s" % (len(text), _NL))
        except OSError:
            pass
    return text

def _read_chars(task_id):
    # Characters of this task printed so far, or None when nothing was counted (then read_chars is not sent).
    if not _safe_id(task_id):
        return None
    try:
        with open(_reads_file(_safe_id(task_id)), encoding="utf-8") as f:
            return sum(int(x) for x in f.read().split() if x.isdigit())
    except OSError:
        return None

def _with_reads(tool, args):
    # The answer and the error of a task tell the server how much of it was read (read_chars): never computed by you.
    if tool in ("publish_response", "report_task_error") and "read_chars" not in args:
        n = _read_chars(args.get("task_id"))
        if n is not None:
            args = dict(args, read_chars=n)
    return args

def _line(value):
    # A value as ONE line of JSON (no raw line break), so pages break between lines and every line that starts with
    # "[[" is one of the helper's own labels or markers.
    text = json.dumps(value, ensure_ascii=False)
    for code in (0x85, 0x2028, 0x2029):
        text = text.replace(chr(code), _BS + "u%04x" % code)
    return text.encode("utf-8", "backslashreplace").decode("utf-8")

def _size(text):
    return len(text.encode("utf-8", "surrogatepass"))

def _cost(lines):
    # [characters, UTF-8 bytes] of lines joined by line breaks.
    return [sum(len(x) for x in lines) + max(0, len(lines) - 1), sum(_size(x) for x in lines) + max(0, len(lines) - 1)]

def _within(cost, room):
    return cost[0] <= room[0] and cost[1] <= room[1]

def _fit(text, chars, room):
    # How many leading characters of text fit in `chars` characters and `room` UTF-8 bytes.
    head = text[:max(0, min(chars, room))]
    data = head.encode("utf-8", "surrogatepass")
    return len(head) if len(data) <= room else len(data[:room].decode("utf-8", "ignore"))

def _human(n):
    return "%d B" % n if n < 1000 else "%.1f KB" % (n / 1000.0) if n < 1000000 else "%.1f MB" % (n / 1000000.0)

def _role(m):
    return str(m.get("role", "?")) if isinstance(m, dict) else "?"

def _chat(task):
    # The conversation of a chat-API task (payload.context.messages), or None for any other task.
    payload = task.get("payload")
    context = payload.get("context") if isinstance(payload, dict) else None
    msgs = context.get("messages") if isinstance(context, dict) else None
    return msgs if isinstance(msgs, list) and msgs else None

def _mline(i, m):
    return ("#%d %s" % (i, _role(m)), _line(m))

def _brief(payload, msgs):
    # payload.prompt repeats the last user message: show it once.
    prompt = payload.get("prompt")
    users = [i for i, m in enumerate(msgs) if _role(m) == "user"]
    if users and isinstance(prompt, str) and len(prompt) > 200 and msgs[users[-1]].get("content") == prompt:
        payload["prompt"] = "(the same text as the content of #%d)" % users[-1]

def _units(task):
    # The whole task as labelled lines (for page()): [[task]] first (its messages and history replaced by a note),
    # then one line per message ([[#i role]]) and per history entry ([[history[i]]]).
    head, msgs, history = dict(task), _chat(task) or [], task.get("history")
    payload = head.get("payload")
    if isinstance(payload, dict) and msgs:
        payload = head["payload"] = dict(payload)
        context = payload["context"] = dict(payload["context"])
        context["messages"] = "(%d messages #0-#%d, one per line below)" % (len(msgs), len(msgs) - 1)
        _images_note(context)
        _brief(payload, msgs)
    if isinstance(history, list) and history:
        head["history"] = "(%d items, one per line below: [[history[0]]] ... [[history[%d]]])" % (len(history), len(history) - 1)
    else:
        history = []
    return ([("task", _line(head))] + [_mline(i, m) for i, m in enumerate(_shown(task))]
            + [("history[%d]" % i, _line(h)) for i, h in enumerate(history)])

def _escapes(text, i):
    # True when text[i] is a backslash that starts a JSON escape (it is not itself escaped).
    j = i
    while j >= 0 and text[j] == _BS:
        j -= 1
    return (i - j) % 2 == 1

def _cut(text, limit):
    # Where to break a text longer than limit: after a line break, an escaped line break or a space close to the limit;
    # otherwise at the limit, but never inside an escape sequence or before a combining mark (no character is lost).
    if len(text) <= limit:
        return len(text)
    limit = max(1, limit)
    low = max(1, limit - max(80, limit // 50))
    for sep in (_NL, _BS + "n", " "):
        i = text.rfind(sep, low, limit)
        while i >= low and sep == _BS + "n" and not _escapes(text, i):
            i = text.rfind(sep, low, i)
        if i >= low:
            return i + len(sep)
    end = limit
    for _ in range(32):
        inside = any(text[j] == _BS and _escapes(text, j) and end < j + (6 if text[j + 1:j + 2] == "u" else 2)
                     for j in range(max(0, end - 6), end))
        if end <= 1 or not (inside or unicodedata.category(text[end])[0] == "M" or chr(0x200d) in text[end - 1:end + 1]):
            break
        end -= 1
    return end

def _pages(units, cap, room):
    # Page bodies of at most cap characters and room UTF-8 bytes. Pages break between lines; a line longer than a page
    # is split into parts labelled PART p/P that continue on the next pages.
    pages, used, size = [[]], 0, 0
    for label, text in units:
        line = "[[" + label + "]] " + text
        sep = 1 if pages[-1] else 0
        bytes_ = _size(line)
        if len(line) <= cap and bytes_ <= room:
            if used + sep + len(line) > cap or size + sep + bytes_ > room:
                pages.append([])
                used = size = sep = 0
            used, size = used + sep + len(line), size + sep + bytes_
            pages[-1].append(line)
            continue
        head = len("[[" + label + " PART 99999/99999]] ")
        if pages[-1] and min(cap - used, room - size) - 1 - head < min(cap, room) // 10:
            pages.append([])
            used = size = 0
        parts = []
        while text:
            sep = 1 if pages[-1] else 0
            n = _cut(text, _fit(text, cap - used - sep - head, room - size - sep - head))
            used, size = used + sep + head + n, size + sep + head + _size(text[:n])
            parts.append((pages[-1], len(pages[-1])))
            pages[-1].append(text[:n])
            text = text[n:]
            if text:
                pages.append([])
                used = size = 0
        for p, (lines, i) in enumerate(parts, 1):
            lines[i] = "[[%s PART %d/%d]] %s" % (label, p, len(parts), lines[i])
    return [_NL.join(lines) for lines in pages if lines]

def _body():
    return [max(1000, PRINT_CAP - 3000), max(1000, PRINT_BYTES - 3000)]

def _layout(units):
    pages = _pages(units, *_body())
    return pages, sum(len(p) for p in pages)

def _split(text, cap):
    # A page cut into parts of at most cap characters and cap UTF-8 bytes (a line break where it is cut is dropped).
    parts = []
    while _size(text) > cap:
        n = _cut(text, _fit(text, cap, cap))
        parts.append(text[:n - 1] if text[n - 1] == _NL else text[:n])
        text = text[n:]
    return parts + [text]

def _span(first, n):
    last = min(first + 7, n)
    return str(first) if last == first else "%d-%d" % (first, last)

def _how(kind, tid, a="K", b=None, c=None):
    # How a note names a helper command: a Python call in the worker chat, a shell command for pool sub-agents. A
    # search query is quoted so that the command still works when it contains quotes.
    if SHELL:
        quote = "'" + str(a).replace("'", "'" + '"' + "'" + '"' + "'") + "'"
        args = {"page": [a], "part": [a, c, b], "ctx": [quote] + ([b] if b else []),
                "search": [quote] + ([b, c] if c else []), "images": []}[kind]
        name = {"part": "page"}.get(kind, kind)
        return "%s (with your SLOT_ID/SLOT_NONCE/SLOT_MAX prefix)" % " ".join(str(x) for x in [SHELL, name, tid] + args)
    if kind == "images":
        return 'images("%s")' % tid
    if kind == "page":
        return 'page("%s", %s)' % (tid, a)
    if kind == "part":
        return 'page("%s", %s, size=%s, part=%s)' % (tid, a, b, c)
    if kind == "ctx":
        return 'ctx("%s", "%s"%s)' % (tid, a, ", %s" % b if b else "")
    return 'ctx_search("%s", %s%s)' % (tid, _line(str(a)), ", %s, %s" % (b, c) if c else "")

def _framed(title, pages, total, k, how, size=None, part=None, parts=None):
    # Page k of a paged output between its markers ([[<title> PAGE k/N]] … END). With part and/or size (page() only):
    # only that part of page k, the page being cut into parts of at most size characters/bytes.
    n, what = len(pages), title.replace("TASK ", "task ", 1)
    if not 1 <= k <= n:
        return "%s has %d page(s): use a page number from 1 to %d." % (what[:1].upper() + what[1:], n, n)
    tag = "[[%s PAGE %d/%d" % (title, k, n)
    chunks = [pages[k - 1]]
    if parts and (size is not None or part is not None):
        size, part = max(2000, size or min(PRINT_CAP, PRINT_BYTES) // 4), part or 1
        chunks = _split(pages[k - 1], size - 1000)
        if not 1 <= part <= len(chunks):
            return "Page %d of %s has %d part(s) of size %d: use a part from 1 to %d." % (k, what, len(chunks), size, len(chunks))
    part, m = part or 1, len(chunks)
    name = tag + (" PART %d/%d" % (part, m) if m > 1 else "")
    out = [name + "]]", chunks[part - 1], name + " END]]"]
    if part < m:
        out.append("Part %d of %d of page %d; the next part continues exactly where this one stops. Next: %s"
                   % (part, m, k, parts(k, size, part + 1)))
        return _NL.join(out)
    if m > 1:
        out.append(tag + " END]]")
    if k == n:
        out.append("[[%s COMPLETE: %d page%s, %d characters]]" % (title, n, "s" if n > 1 else "", total))
        if n > 1:
            out.append("That was the last page: answer only after reading all %d pages." % n)
    elif m > 1:
        out.append("Next: " + parts(k + 1, size, 1))
    elif k == 1:
        out.append("This %s has %d pages: read ALL of them before answering. Fetch the others in PARALLEL: ONE message "
                   "with up to 8 executions, each running only %s for one page K: pages %s now, then the next 8, and "
                   "so on up to page %d." % ("task" if " " not in title[5:] else "result", n, how("K"), _span(2, n), n))
    elif (k - 1) % 8 == 0:
        out.append("Next batch, in ONE message with one execution per page: pages %s, each with %s." % (_span(k + 1, n), how("K")))
    return _NL.join(out)

def _frame(task, k=1, size=None, part=None):
    tid = task.get("task_id")
    pages, total = _layout(_units(task))
    return _framed("TASK %s" % tid, pages, total, k, lambda K: _how("page", tid, K), size, part,
                   lambda K, s, p: _how("part", tid, K, s, p))

def _tool_name(t):
    f = t.get("function") if isinstance(t, dict) else None
    return str(f.get("name", "?")) if isinstance(f, dict) else "?"

def _history(task):
    history = task.get("history")
    return history if isinstance(history, list) else []

def _system(task, msgs):
    # The system part of a chat task: [[task]] (metadata), [[instructions]], the system/developer messages (one quoted
    # word for word in the instructions is not repeated), earlier tasks of the conversation ([[history[i]]], if any),
    # plus the tool definitions, one [[tool k name]] line each.
    head, history = dict(task), _history(task)
    if history:
        head["history"] = "(%d items, one per line below: [[history[0]]] ... [[history[%d]]])" % (len(history), len(history) - 1)
    payload = head["payload"] = dict(head["payload"])
    context = payload["context"] = dict(payload["context"])
    context["messages"] = "(%d messages #0-#%d)" % (len(msgs), len(msgs) - 1)
    _images_note(context)
    contract = context.get("output_contract")
    tools = contract.get("tools") if isinstance(contract, dict) else None
    tools = tools if isinstance(tools, list) else []
    if tools:
        contract = context["output_contract"] = dict(contract)
        contract["tools"] = "(%d tools: %s)" % (len(tools), ", ".join(_tool_name(t) for t in tools))
    text = payload.get("instructions") if isinstance(payload.get("instructions"), str) else ""
    if text:
        payload["instructions"] = "(see [[instructions]])"
    _brief(payload, msgs)
    units = [("task", _line(head))] + ([("instructions", _line(text))] if text else [])
    for i, m in enumerate(msgs):
        body = m.get("content") if isinstance(m, dict) else None
        if _role(m) in _SYS:
            quoted = isinstance(body, str) and len(body) > 40 and body in text
            units.append(("#%d %s" % (i, _role(m)), '"(quoted word for word in [[instructions]])"' if quoted else _line(m)))
    units += [("history[%d]" % i, _line(h)) for i, h in enumerate(history)]
    return units, [("tool %d %s" % (k, _tool_name(t)), _line(t)) for k, t in enumerate(tools)]

def _request(msgs):
    # The request itself: the last user message, plus the last assistant turn and everything after it when that turn
    # comes later (fresh tool results, or an assistant prefill to continue).
    roles = [_role(m) for m in msgs]
    u = max([i for i, r in enumerate(roles) if r == "user"] or [-1])
    a = max([i for i, r in enumerate(roles) if r == "assistant"] or [-1])
    tail = list(range(a, len(msgs))) if a > u else list(range(max(u, 0), len(msgs)))
    return [i for i in sorted(set(tail + ([u] if u >= 0 else []))) if roles[i] not in _SYS]

def _selection(ids):
    # A compact selection for ctx(): "#3,#7-#9".
    out, i = [], 0
    while i < len(ids):
        j = i
        while j + 1 < len(ids) and ids[j + 1] == ids[j] + 1:
            j += 1
        out.append("#%d" % ids[i] if i == j else "#%d-#%d" % (ids[i], ids[j]))
        i = j + 1
    return ",".join(out)

def _squeeze(text, n):
    text = " ".join(str(text).split())
    return text if len(text) <= n else text[:n - 1] + "…"

def _entry(i, m, names, size, pics=()):
    # One index line: "#n role size preview", tool calls as name(short args), tool results as tool name + size; then the
    # images of the message ([image N: <file> (...)]).
    role = _role(m)
    shown = "".join(" " + p for p in pics)
    if role == "tool":
        tool = names.get(m.get("tool_call_id")) or m.get("name") or "?"
        return "#%d tool %s %s%s%s" % (i, tool, _human(size), " (error)" if m.get("is_error") else "", shown)
    out = "#%d %s %s" % (i, role, _human(size))
    body = m.get("content") if isinstance(m.get("content"), str) else ""
    if body.strip():
        out += " " + _line(_squeeze(body, 60))
    calls = [c for c in (m.get("tool_calls") or []) if isinstance(c, dict)]
    if calls:
        sig = ["%s(%s)" % (_tool_name(c), _squeeze((c.get("function") or {}).get("arguments", ""), 40)) for c in calls[:3]]
        out += " -> " + ", ".join(sig) + (" +%d more" % (len(calls) - 3) if len(calls) > 3 else "")
    return out + shown

def _index(omitted, msgs, sizes, shown, room, pics=None):
    # One line per omitted message; too many for `room` ⇒ the first and last few stay, the runs between them become
    # range lines (a range never spans a message that is shown).
    names = {}
    for m in msgs:
        for c in (m.get("tool_calls") or []) if isinstance(m, dict) else []:
            if isinstance(c, dict):
                names[c.get("id")] = _tool_name(c)
    lines = [_entry(i, msgs[i], names, sizes[i], [p for _, p in (pics or {}).get(i, [])]) for i in omitted]
    if _within(_cost(lines), room):
        return lines
    for first, last in ((3, 12), (3, 8), (2, 5), (1, 3), (1, 1), (0, 0)):
        if first + last < len(omitted):
            out = lines[:first] + _ranges(omitted[first:len(omitted) - last], sizes, shown) + lines[len(omitted) - last:]
            if _within(_cost(out), room):
                return out
    return _ranges(omitted, sizes, set())[:1]

def _ranges(ids, sizes, shown):
    runs = [[ids[0]]] if ids else []
    for i in ids[1:]:
        if any(j in shown for j in range(runs[-1][-1] + 1, i)):
            runs.append([i])
        else:
            runs[-1].append(i)
    out = []
    for run in runs:
        step = max(1, -(-len(run) // 4))
        for k in range(0, len(run), step):
            part = run[k:k + step]
            out.append("#%d-#%d: %d messages, %s — use ctx_search or ctx" % (part[0], part[-1], len(part), _human(sum(sizes[i] for i in part))))
    return out

def _view(task, reserve=(0, 0)):
    # The first read of a conversation, in ONE output: header, system part, an INDEX of the older messages that are not
    # shown, then the newest messages in full (the request itself always complete, or paged and announced). `reserve`
    # = what the same output already holds (the call result line); a result that would not fit is built again smaller.
    cap = [PRINT_CAP - reserve[0], PRINT_BYTES - reserve[1]]
    room = [cap[0] - 900, cap[1] - 900]
    for _ in range(4):
        text = _view_in(task, room)
        over = _cost([text])
        if _within(over, cap):
            return text
        room = [room[0] - max(0, over[0] - cap[0]) - 200, room[1] - max(0, over[1] - cap[1]) - 200]
    return text

def _view_in(task, room):
    tid, msgs = task.get("task_id"), _chat(task)
    sys_units, tool_units = _system(task, msgs)
    pics = _pictures(task)
    units = dict((i, _mline(i, m)) for i, m in enumerate(_shown(task)) if _role(m) not in _SYS)
    lines = dict((i, "[[%s]] %s" % u) for i, u in units.items())
    sizes = dict((i, _size(x)) for i, x in lines.items())
    req = _request(msgs)
    older = [i for i in sorted(units) if i not in req]
    sys_lines = ["[[%s]] %s" % u for u in sys_units]
    tool_lines = ["[[%s]] %s" % u for u in tool_units]
    req_cost = _cost([lines[i] for i in req])
    paged = not _within([req_cost[0] + 2000, req_cost[1] + 2000], room)
    # The request is shown whole, or (longer than one output) only announced with the ctx() call that reads it.
    rest = [room[0] - 700, room[1] - 700] if paged else [room[0] - req_cost[0] - 401, room[1] - req_cost[1] - 401]
    window = []
    if _within(_cost(sys_lines + tool_lines + [lines[i] for i in older]), rest):
        window = older
    else:
        # Newest-first fill of a CONTIGUOUS run of older messages; what the index and the system part leave unused
        # goes back to the window (a few rounds, so the result stays the same for the same task).
        full = _cost(sys_lines + tool_lines)
        sys_room = [min(full[0], rest[0] // 2), min(full[1], rest[1] // 2)]
        index_room = [min(3000, rest[0] // 4), min(3000, rest[1] // 4)]
        for _ in range(3):
            left, grown = [rest[0] - sys_room[0] - index_room[0], rest[1] - sys_room[1] - index_room[1]], []
            for i in reversed(older):
                line = _cost([lines[i]])
                if not _within([line[0] + 1, line[1] + 1], left):
                    break
                grown.insert(0, i)
                left = [left[0] - line[0] - 1, left[1] - line[1] - 1]
            if window and len(grown) <= len(window):
                break
            gone = [i for i in older if i not in grown]
            used = _cost(_index(gone, msgs, sizes, set(grown) | set(req), index_room, pics) + ["[[INDEX]] x" * 2]) if gone else [0, 0]
            if not _within([used[0], used[1]], index_room):
                break
            window, index_room = grown, used
    shown = set(window) | (set() if paged else set(req))
    omitted = [i for i in older if i not in shown]
    index = []
    if omitted:
        index = ["[[INDEX]] %d older messages NOT shown here (fetch any with ctx or ctx_search):" % len(omitted)]
        index += _index(omitted, msgs, sizes, shown | set(req), [min(3000, rest[0] // 4), min(3000, rest[1] // 4)], pics)
    body = [lines[i] for i in sorted(shown)]
    used = _cost(index + [lines[i] for i in window])
    left = [rest[0] - used[0] - 1, rest[1] - used[1] - 1]
    system, cut = _clip(sys_lines + tool_lines, left)
    if cut and tool_lines:
        system, cut = _clip(sys_lines, [left[0] - 150, left[1] - 150])
        system.append("[[tools]] %d tool definitions NOT shown: %s" % (len(tool_lines), _how("ctx", tid, "tools")))
    if cut:
        system.append("[[system continues: %s]]" % _how("ctx", tid, "system"))
    total = sum(sizes.values()) + _cost(sys_lines + tool_lines)[1]
    head = "[[TASK %s WINDOW]] %d messages (#0-#%d), %s in all. " % (tid, len(msgs), len(msgs) - 1, _human(total))
    if not omitted and not cut:
        head += "Everything else is shown below." if paged else "Everything is shown below."
    else:
        head += ("Below: the system part, an INDEX of older messages that are NOT shown, then the newest messages in "
                 "full. Anything your answer needs that is not shown: fetch it first, with %s or %s."
                 % (_how("ctx", tid, "#12-#20"), _how("search", tid, "words")))
    tail = []
    if paged:
        sel = _selection(req)
        pages = len(_layout([units[i] for i in req])[0])
        note = ("The request itself (%s, %s) is longer than one output: read ALL of it now, %d page%s, in PARALLEL "
                "(ONE message, up to 8 executions): %s." % (sel, _human(req_cost[1]), pages, "s" if pages > 1 else "",
                                                           _how("ctx", tid, sel, "K") if pages > 1 else _how("ctx", tid, sel)))
        head, tail = head + " " + note, ["[[REQUEST]] " + note]
    return _NL.join([head] + system + index + body + tail + ["[[TASK %s WINDOW END]]" % tid])

def _clip(lines, room):
    # The leading lines that fit in room (the first line that does not fit is cut at a clean point); True if cut.
    out, used = [], [0, 0]
    for line in lines:
        c = _cost([line])
        if _within([used[0] + c[0] + 1, used[1] + c[1] + 1], room):
            out.append(line)
            used = [used[0] + c[0] + 1, used[1] + c[1] + 1]
            continue
        n = _cut(line, _fit(line, room[0] - used[0] - 1, room[1] - used[1] - 1))
        if n > 40:
            out.append(line[:n])
        return out, True
    return out, False

def _images_note(context):
    # The image metadata of a task is not printed as such: each image is shown where it appears in its message.
    if isinstance(context.get("attachments"), list) and context["attachments"]:
        n = len(context["attachments"])
        context["attachments"] = "(%d image%s, each shown where it appears)" % (n, "" if n == 1 else "s")

def _attachments(task):
    # The images of a task (payload.context.attachments): [{"n", "message", "media_type", "width", "height", "bytes", "sha256"}].
    payload = task.get("payload") if isinstance(task, dict) else None
    context = payload.get("context") if isinstance(payload, dict) else None
    items = context.get("attachments") if isinstance(context, dict) else None
    if not isinstance(items, list):
        return []
    return [a for a in items if isinstance(a, dict) and isinstance(a.get("n"), int) and isinstance(a.get("sha256"), str)]

def _image_dir(task_id):
    home = next((h for h in IMAGE_HOMES if os.path.isdir(h)), IMAGE_HOMES[-1])
    key = hashlib.sha256(("%s|%s" % (WORKER_ID, task_id)).encode("utf-8")).hexdigest()[:12]
    return os.path.join(home, IMAGE_FOLDER, key)

def _image_path(task_id, a):
    return os.path.join(_image_dir(task_id), "image-%d.%s" % (a["n"], _EXTENSIONS.get(a.get("media_type"), "img")))

def _picture(task, a):
    # How an image is shown in place of its [image N]: its saved file with format, size and weight, or the command that
    # fetches it first.
    tid = task.get("task_id")
    info = "%s %s%s%s, %s" % (_FORMATS.get(a.get("media_type"), "image"), a.get("width", "?"), chr(0xd7), a.get("height", "?"),
                              _human(int(a.get("bytes") or 0)))
    path = _image_path(tid, a) if _safe_id(tid) else ""
    if path and os.path.isfile(path):
        return "[image %d: %s (%s)]" % (a["n"], path, info)
    return "[image %d: not downloaded yet, run %s (%s)]" % (a["n"], _how("images", tid), info)

def _pictures(task):
    # {message number: [(N, how image N is shown), ...]}.
    out = {}
    for a in sorted(_attachments(task), key=lambda a: a["n"]):
        if isinstance(a.get("message"), int):
            out.setdefault(a["message"], []).append((a["n"], _picture(task, a)))
    return out

def _shown(task):
    # The messages as you see them: in each message, [image N] becomes how image N is shown (its file, format and size).
    msgs, pics = _chat(task) or [], _pictures(task)
    if not pics:
        return msgs
    out = []
    for i, m in enumerate(msgs):
        text = m.get("content") if isinstance(m, dict) else None
        if i not in pics or not isinstance(text, str):
            out.append(m)
            continue
        for n, picture in pics[i]:
            token = "[image %d]" % n
            at = text.find(token)
            text = text[:at] + picture + text[at + len(token):] if at >= 0 else text + _NL + picture
        out.append(dict(m, content=text))
    return out

def _fetch_part(task_id, n, offset, length, timeout):
    # Bytes [offset, offset + length) of image n of a task you hold (the server checks the lease).
    url = (MCP_URL[:-4] if MCP_URL.endswith("/mcp") else MCP_URL.rstrip("/")) + "/bridge/v1/attachment"
    data = json.dumps(dict(lease(task_id), index=n, offset=offset, length=length)).encode("utf-8")
    headers = {"Content-Type": "application/json", "Accept": "application/octet-stream",
               "Authorization": "Bearer " + TOKEN, "User-Agent": "glm-web-worker/1.0"}
    req = urllib.request.Request(url, data=data, method="POST", headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()

def _sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()

def _download_one(task_id, a, deadline):
    # Fetch one image in parts into <file>.part (a part cut by the end of an execution is continued by the next call),
    # check its sha256, then give it its final name. True = saved.
    path = _image_path(task_id, a)
    part, total = path + ".part", int(a.get("bytes") or 0)
    for _ in range(2):
        done, failures = (os.path.getsize(part) if os.path.isfile(part) else 0), 0
        while done < total:
            left = deadline - time.monotonic()
            if left < 4:
                return False
            try:
                data = _fetch_part(task_id, a["n"], done, min(FILE_CHUNK, total - done), max(1.0, min(60.0, left - 2)))
            except urllib.error.HTTPError as e:
                if e.code not in (502, 503, 504):
                    raise
                data = b""
            except (OSError, http.client.HTTPException):
                data = b""
            if not data:
                failures += 1
                if failures > 3:
                    return False
                time.sleep(min(2.0 * failures, max(0.0, deadline - time.monotonic() - 4)))
                continue
            with open(part, "ab") as f:
                f.write(data)
            done += len(data)
        if done == total and _sha256_file(part) == a.get("sha256"):
            os.replace(part, path)
            return True
        _drop(part)  # not the expected image: fetch it once more from the start
    return False

def _download(task):
    # Save every image of a task that is not saved yet (the images of the request first) within this execution.
    # Returns how many are still missing.
    tid, items = task.get("task_id"), _attachments(task)
    if not items or not _safe_id(tid):
        return 0
    try:
        os.makedirs(_image_dir(tid), exist_ok=True)
    except OSError:
        return len(items)
    deadline = _execution() + EXEC_SECONDS - 6
    first = set(_request(_chat(task) or []))
    missing = 0
    for a in sorted(items, key=lambda a: (a.get("message") not in first, a["n"])):
        if os.path.isfile(_image_path(tid, a)):
            continue
        try:
            saved = _download_one(tid, a, deadline)
        except (OSError, RuntimeError, http.client.HTTPException):
            saved = False  # refused (lease lost, image gone) or unreachable: it stays "not downloaded yet"
        missing += 0 if saved else 1
    return missing

def _drop_images(task_id):
    # Delete the saved images of a task (its answer is stored, or the task is forgotten).
    if not _safe_id(task_id):
        return
    folder = _image_dir(task_id)
    for name in os.listdir(folder) if os.path.isdir(folder) else []:
        _drop(os.path.join(folder, name))
    try:
        os.rmdir(folder)
    except OSError:
        pass

def _images(task_id):
    task = _saved(task_id)
    if isinstance(task, str):
        return task
    items = sorted(_attachments(task), key=lambda a: a["n"])
    if not items:
        return "This task has no images."
    missing = _download(task)
    note = ("Open each image you need with your Read tool." if not missing else
            "%d image(s) are not downloaded yet: run this command again." % missing)
    return _NL.join(["Images of task %s:" % task.get("task_id")] + [_picture(task, a) for a in items] + [note])

def images(task_id):
    # Download the images of a task you received (those not saved yet) and list their files.
    print(_images(task_id))

class Paged(dict):
    # The result of a call that delivered a task. result["task"] (or result["next_task"]) is the complete task, but
    # printing the result shows the call result and the first read of the task, never more than one output can show:
    # a WINDOW for a conversation, page 1 for any other task.
    def __str__(self):
        key = "task" if isinstance(self.get("task"), dict) else "next_task"
        task, info = self[key], dict(self)
        msgs = _chat(task)
        if msgs:
            info[key] = {"task_id": task.get("task_id"), "messages": len(msgs), "shown": "window below"}
            text = None
        else:
            pages, total = _layout(_units(task))
            info[key] = {"task_id": task.get("task_id"), "pages": len(pages), "characters": total, "shown": "below"}
            text = _frame(task, 1)
        for name, value in info.items():
            if isinstance(value, str) and len(value) > 1000:
                info[name] = value[:1000] + " ...(cut)"
        top = _line(info)
        if text is None:
            text = _view(task, [c + 1 for c in _cost([top])])
        return top + _NL + _counted(task.get("task_id"), text)
    __repr__ = __str__

def _keep(result):
    # Remember the lease_token of every task you receive, so you never copy it by hand, and save the whole task to its
    # own file, so that page(), ctx() and ctx_search() can show any part of it (they never call the server).
    task = (result or {}).get("task") or (result or {}).get("next_task")
    if not task:
        return result
    leases = _load(LEASES)
    leases[task["task_id"]] = task["lease_token"]
    kept = dict(list(leases.items())[-50:])
    _save(LEASES, kept)
    for old in [t for t in leases if t not in kept]:
        _drop(_task_file(old))
        _drop(_reads_file(old))
        _drop_images(old)
    try:
        with open(_task_file(task["task_id"]), "w", encoding="utf-8") as f:
            json.dump(task, f)
    except OSError:
        pass  # the first read is still shown; only page()/ctx()/ctx_search() cannot show this task again
    _download(task)  # the images of the task, before its first read is printed
    return Paged(result)

def _wait(until, once=True):
    # Chain long-polls (each at most POLL_SECONDS) until a task arrives or the monotonic time `until` passes. A server
    # or tunnel that cannot be reached until then counts as no task: the next take() simply tries again.
    while True:
        left = until - time.monotonic()
        if left < min(3.0, POLL_SECONDS / 2.0) and not once:
            return {"status": "timeout"}
        once, poll = False, max(1.0, min(POLL_SECONDS, left))
        try:
            r = _call("wait_for_task", {"worker_id": WORKER_ID, "timeout_ms": int(poll * 1000), "ack": True,
                                        "context_session": CONTEXT_SESSION}, poll + 10)
        except urllib.error.HTTPError as e:
            if e.code not in (502, 503, 504):
                raise
            return {"status": "timeout"}
        except (OSError, http.client.HTTPException):
            return {"status": "timeout"}
        if not isinstance(r, dict) or r.get("status") not in ("timeout", "aborted"):
            return r
        time.sleep(min(max(0, until - time.monotonic()), (r.get("retry_after_ms") or 0) / 1000.0))

def take(timeout_ms=None):
    # Wait for your next task: up to WAIT_SECONDS (or timeout_ms) in this ONE execution; returns as soon as a task
    # arrives. No task: just {"status": "timeout"} -> run take() again.
    seconds = WAIT_SECONDS if timeout_ms is None else min(WAIT_SECONDS, timeout_ms / 1000.0)
    r = _wait(_execution() + seconds)
    if isinstance(r, dict) and r.get("status") in ("timeout", "superseded") and not r.get("task"):
        return {"status": r["status"]}
    return _keep(r)

def _saved(task_id):
    # The saved copy of a task you received, or an error text.
    task_id = str(task_id)
    try:
        if not task_id or not all(c.isalnum() or c in "_.:-" for c in task_id):
            raise ValueError(task_id)
        with open(_task_file(task_id), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return "No saved copy of task " + task_id + " here (wrong id, or its answer is already stored): receive it again with take."

def _page(task_id, k=1, size=None, part=None):
    try:
        k, size, part = int(k), (int(size) if size else None), (int(part) if part else None)
    except (TypeError, ValueError):
        return "page, size and part must be whole numbers."
    task = _saved(task_id)
    return task if isinstance(task, str) else _counted(task_id, _frame(task, k, size, part))

def page(task_id, k=1, size=None, part=None):
    # Show page k of the WHOLE task, from its saved copy (several page() calls may run in parallel). A page that was
    # cut off: show it in parts with page(TASK_ID, k, part=1), then the part named at its end (size = most bytes).
    print(_page(task_id, k, size, part))

def _pick(task, sel):
    # The lines of a ctx() selection and its canonical name, or an error text.
    msgs = _chat(task) or []
    sel = str(sel).strip()
    if sel in ("system", "tools"):
        if not msgs:
            return [u for u in _units(task) if u[0] == "task" or u[0].startswith("history[")], sel
        units, tools = _system(task, msgs)
        return (units if sel == "system" else tools or [("tools", '"(this task declares no tools)"')]), sel
    if not msgs:
        return "Task %s has no messages: read it with %s." % (task.get("task_id"), _how("page", task.get("task_id")))
    ids = []
    for item in sel.replace(" ", "").replace(chr(0x2013), "-").split(","):
        bounds = item.replace("#", "").split("-")
        try:
            a, b = int(bounds[0]), int(bounds[-1])
        except ValueError:
            return 'Unknown selection %s: use "#12-#20", "#3,#7,#9", "system" or "tools".' % _line(sel)
        if len(bounds) > 2 or not 0 <= a <= b < len(msgs):
            return "Selection %s is outside messages #0-#%d." % (_line(sel), len(msgs) - 1)
        ids.extend(range(a, b + 1))
    ids = sorted(set(ids))
    shown = _shown(task)
    return [_mline(i, shown[i]) for i in ids], _selection(ids)

def _ctx(task_id, sel, k=1):
    try:
        k = int(k)
    except (TypeError, ValueError):
        return "The page number must be a whole number."
    task = _saved(task_id)
    if isinstance(task, str):
        return task
    picked = _pick(task, sel)
    if isinstance(picked, str):
        return picked
    units, name = picked
    tid = task.get("task_id")
    pages, total = _layout(units)
    return _counted(tid, _framed("TASK %s CTX %s" % (tid, name), pages, total, k, lambda K: _how("ctx", tid, name, K)))

def ctx(task_id, sel, k=1):
    # Show part of a task you received, from its saved copy (no server call): messages "#12-#20" or "#3,#7,#9", "system"
    # (metadata, instructions, system messages) or "tools" (tool definitions). A long result comes in pages: ctx(.., k).
    print(_ctx(task_id, sel, k))

def _text(m):
    # The searchable text of a message: its content plus its tool calls.
    body = m.get("content") if isinstance(m, dict) else None
    out = body if isinstance(body, str) else (json.dumps(body, ensure_ascii=False) if body else "")
    for c in (m.get("tool_calls") or []) if isinstance(m, dict) else []:
        if isinstance(c, dict):
            out += _NL + "%s(%s)" % (_tool_name(c), (c.get("function") or {}).get("arguments", ""))
    return out

def _search(task_id, query, max_hits=20, k=1):
    try:
        max_hits, k = max(1, int(max_hits)), int(k)
    except (TypeError, ValueError):
        return "max_hits and the page number must be whole numbers."
    task = _saved(task_id)
    if isinstance(task, str):
        return task
    q = str(query)
    if len(q) > 2 and q.startswith("/") and q.endswith("/"):
        try:
            pattern = re.compile(q[1:-1], re.I)
        except re.error as e:
            return "Invalid regular expression %s: %s" % (_line(q), e)
    elif q:
        pattern = re.compile(re.escape(q), re.I)
    else:
        return "Empty query."
    msgs = _chat(task) or []
    payload = task.get("payload") if isinstance(task.get("payload"), dict) else {}
    sources = [("#%d %s" % (i, _role(m)), _text(m)) for i, m in enumerate(msgs)]
    if not msgs:
        sources.append(("prompt", str(payload.get("prompt") or "")))
    sources.append(("instructions", str(payload.get("instructions") or "")))
    sources.append(("tools", "".join(_line(t) for t in ((payload.get("context") or {}).get("output_contract") or {}).get("tools") or [])))
    sources += [("history[%d]" % i, _line(h)) for i, h in enumerate(_history(task))]
    hits, places, count = [], [], 0
    for label, body in sources:
        end = -1
        for found in pattern.finditer(body):
            if found.end() == found.start():
                continue
            count += 1
            if label not in places:
                places.append(label)
            if found.start() >= end and len(hits) < max_hits:
                a, b = max(0, found.start() - 200), min(len(body), found.end() + 200)
                hits.append((label, _line(("…" if a else "") + body[a:b] + ("…" if b < len(body) else ""))))
                end = b
            if count >= 100000:
                break
    tid = task.get("task_id")
    summary = ("%d match%s in %d place%s (%s); %d snippet%s below (max_hits=%d)." % (
        count, "es" if count != 1 else "", len(places), "s" if len(places) != 1 else "", ", ".join(places[:30]),
        len(hits), "s" if len(hits) != 1 else "", max_hits) if count else "No match for %s." % _line(q))
    pages, total = _layout([("search", summary)] + hits)
    name = "SEARCH %s" % _line(_squeeze(q, 60))
    return _counted(tid, _framed("TASK %s %s" % (tid, name), pages, total, k, lambda K: _how("search", tid, q, max_hits, K)))

def ctx_search(task_id, query, max_hits=20, k=1):
    # Find text in a task you received, from its saved copy (no server call): case-insensitive; "/.../" = a regular
    # expression. Prints each match with ~200 characters around it, its message number and role.
    print(_search(task_id, query, max_hits, k))

def lease(task_id):
    token = _load(LEASES).get(task_id)
    if token is None:
        raise RuntimeError("no lease_token remembered for " + task_id + ": run take() to receive the task again")
    return {"worker_id": WORKER_ID, "task_id": task_id, "lease_token": token}

def tool(name, task_id, **args):
    return call(name, **lease(task_id), **args)

def _stored(task_id, result, files=()):
    # The answer is stored: delete this task's images; with CLEANUP also its files, its lease and its sent sections.
    if not isinstance(result, dict) or "error" in result:
        return
    _drop_images(task_id)
    if not CLEANUP:
        return
    sent = _load(CHUNKS)
    files = list(files) + sent.pop(task_id + "|files", []) + [_task_file(task_id), _reads_file(task_id)]
    for key in [k for k in sent if k == task_id or k.startswith(task_id + "|")]:
        del sent[key]
    _save(CHUNKS, sent)
    leases = _load(LEASES)
    if leases.pop(task_id, None) is not None:
        _save(LEASES, leases)
    for path in files:
        _drop(path)

def publish(task_id, path=None, content="", last=False, **extra):
    # Store the complete answer, then wait for your next task in the same execution (up to WAIT_SECONDS in all, like
    # take()), unless last=True. An answer read from a file loses exactly ONE trailing line break (a heredoc adds one).
    start = _execution()
    if path is not None:
        with open(path, encoding="utf-8") as f:
            content = f.read()
        content = content[:-1] if content.endswith(_NL) else content
    extra.setdefault("format", "markdown")
    if not last:
        extra["next"] = {"timeout_ms": int(min(POLL_SECONDS, WAIT_SECONDS) * 1000), "context_session": CONTEXT_SESSION}
    result = _call("publish_response", _with_reads("publish_response", dict(lease(task_id), content=content, **extra)), POLL_SECONDS + 10)
    _stored(task_id, result, [path] if path else [])
    if last or not isinstance(result, dict) or "error" in result:
        return _keep(result)
    if result.get("next_status") in ("timeout", "aborted"):
        try:
            nxt = _wait(start + WAIT_SECONDS, once=False)
        except Exception:
            nxt = {"status": "timeout"}  # the answer IS stored; the next take() reports whatever went wrong
        if nxt.get("status") == "task":
            result.update(next_status="task", next_task=nxt.get("task"), next_action="Response stored. " + str(nxt.get("next_action", "")))
        elif nxt.get("status") in ("session_exhausted", "session_retired", "session_should_end"):
            result.update(next_status=nxt["status"], next_task=None, next_action=nxt.get("next_action"), message=nxt.get("message"))
    if result.get("next_status") in ("timeout", "aborted"):
        short = dict((k, result[k]) for k in ("task_id", "status", "duplicate") if k in result)
        short["next_status"] = "timeout"
        return short
    return _keep(result)

def chunk(task_id, path, channel="answer", **extra):
    # Send the NEXT section of a streamed answer (publish_chunk); sections are numbered per channel for you.
    # channel="reasoning" sends a summary of your reasoning instead: never part of the final answer.
    with open(path, encoding="utf-8") as f:
        text = f.read()
    key = task_id if channel == "answer" else task_id + "|" + channel
    sent = _load(CHUNKS)
    parts = sent.get(key, [])
    hold = False
    if channel == "answer":
        # The answer must not end with the line break a heredoc adds: one trailing line break of each section is held
        # back and sent in front of the next section, so the sections sent always join to the final answer.
        text = (_NL if sent.get(task_id + "|nl") else "") + text
        hold = text.endswith(_NL)
        text = text[:-1] if hold else text
    else:
        extra["channel"] = channel
    if text:
        result = _call("publish_chunk", dict(lease(task_id), sequence=len(parts), delta=text, **extra))
    else:
        result = {"sequence": len(parts), "duplicate": False, "held": True}
    if "error" not in result:
        if text:
            sent[key] = parts + [text if channel == "answer" else ""]
        if channel == "answer":
            sent[task_id + "|nl"] = hold
        if CLEANUP:
            sent[task_id + "|files"] = sent.get(task_id + "|files", []) + [path]
        _save(CHUNKS, dict(list(sent.items())[-60:]))
    return result

def finish(task_id, last=False, **extra):
    # Publish the full answer = every answer section already sent, in order (reasoning is not part of it).
    parts = _load(CHUNKS).get(task_id, [])
    if not parts:
        return {"error": {"code": "nothing_sent", "message": "No answer section of this task was sent yet: send it with chunk, or use publish."}}
    return publish(task_id, content="".join(parts), last=last, **extra)

def _args(argv):
    # Split a command line into positional arguments and the options --note 'text', --channel NAME, --last.
    opts, rest, i = {}, [], 0
    while i < len(argv):
        if argv[i] in ("--note", "--channel") and i + 1 < len(argv):
            opts[argv[i][2:]], i = argv[i + 1], i + 2
        elif argv[i] == "--last":
            opts["last"], i = True, i + 1
        else:
            rest.append(argv[i])
            i += 1
    return rest, opts

def _cli(argv):
    # publish TASK_ID FILE | chunk TASK_ID FILE | finish TASK_ID | page TASK_ID K [PART [SIZE]] | ctx TASK_ID SEL [K]
    # | search TASK_ID QUERY [MAX_HITS [K]] | images TASK_ID, with options --note 'text', --channel reasoning, --last.
    rest, opts = _args(argv)
    extra = {"public_note": opts["note"]} if opts.get("note") else {}
    last = opts.get("last", False)
    if len(rest) == 3 and rest[0] == "publish":
        return publish(rest[1], rest[2], last=last, **extra)
    if len(rest) == 3 and rest[0] == "chunk":
        return chunk(rest[1], rest[2], channel=opts.get("channel", "answer"), **extra)
    if len(rest) == 2 and rest[0] == "finish":
        return finish(rest[1], last=last, **extra)
    if 3 <= len(rest) <= 5 and rest[0] == "page":
        more = rest[3:] + [None, None]
        return _page(rest[1], rest[2], size=more[1], part=more[0])
    if 3 <= len(rest) <= 4 and rest[0] == "ctx":
        return _ctx(rest[1], rest[2], *rest[3:])
    if 3 <= len(rest) <= 5 and rest[0] == "search":
        return _search(rest[1], rest[2], *rest[3:])
    if len(rest) == 2 and rest[0] == "images":
        return _images(rest[1])
    return None

if __name__ == "__main__" and len(sys.argv) > 1:
    _out = _cli(sys.argv[1:])
    if _out is not None:
        print(_out if isinstance(_out, (str, Paged)) else json.dumps(_out, ensure_ascii=False))
