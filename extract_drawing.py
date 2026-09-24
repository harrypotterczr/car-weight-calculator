# -*- coding: utf-8 -*-
"""
图纸参数识别（供轿厢重量计算器网页调用）
用法: python extract_drawing.py <图纸文件路径>   (.pdf / .dxf)
输出: stdout 末尾以 ===RESULT_JSON=== 标记输出 JSON（所有日志走 stderr）

识别策略（按可靠性分层，只针对网页列出的参数）:
  层1  强证据: "KEY=value" 标注（如 CA=1350 / 轿厢宽度=1350）
  层1b 同行邻近: "CA（CAR WIDTH） 1350" 标签后同行最近的数值
  层2  短语匹配: CAR INTERNAL / CAPACITY: 1600 KG / OPENING 1100 等
同一参数多个候选值时全部返回（多梯号图纸存在差异），由网页端让用户选择。
"""
import sys, os, re, json

MARKER = "===RESULT_JSON==="

def log(*a):
    print(*a, file=sys.stderr)

# ---------------------------------------------------------------- 基础配置

# 层1: 标注键 -> 网页参数
KEY_ALIAS = {
    'CA': 'CA', 'CB': 'CB', 'CH': 'CH', 'RH': 'CH',   # RH 为 CH 的备选证据
    'PL': 'JJ', 'LH': 'HH', 'JJ': 'JJ', 'HH': 'HH',
    'SW': 'SW', 'EA': 'EA', 'FT': 'floorThickness',
}

# 中文标注键 -> 网页参数（要求单位 kg 的除外）
CN_LABELS = {
    '轿厢宽度': 'CA', '轿宽': 'CA',
    '轿厢深度': 'CB', '轿深': 'CB',
    '轿厢高度': 'CH', '内净高': 'CH',
    '开门宽度': 'JJ', '门宽': 'JJ', '门开口宽': 'JJ',
    '开门高度': 'HH', '门高': 'HH', '门开口高': 'HH',
    '地坎宽度': 'SW', '地坎宽': 'SW',
    '地板厚度': 'floorThickness',
    '额定载重': 'capacity', '载重量': 'capacity',
    '额定速度': 'speed',
}

KEY_DESC = {
    'CA': '轿厢宽度CA(mm)', 'CB': '轿厢深度CB(mm)', 'CH': '轿厢高度CH/RH(mm)',
    'HH': '开门高度HH(mm)', 'JJ': '开门宽度JJ(mm)', 'SW': '地坎宽度SW(mm)',
    'EA': 'EA(mm)', 'floorThickness': '地板厚度(mm)',
    'capacity': '载重(kg)', 'speed': '速度(m/s)',
    'openingType': '开门方式', 'elevatorModel': '电梯型号',
}

# 合理性区间（超范围直接丢弃，保证识别质量）
RANGES = {
    'CA': (300, 5000), 'CB': (300, 5000), 'CH': (300, 5000),
    'HH': (300, 5000), 'JJ': (300, 5000),
    'SW': (10, 1000), 'EA': (10, 2000), 'floorThickness': (5, 200),
    'capacity': (200, 30000), 'speed': (0.3, 18),
}

NUM_RE = r'([-+]?\d+(?:[.,]\d+)?)'


def norm_num(s):
    """数值规范化: 127,5 -> 127.5 (欧洲小数逗号); 1,350 -> 1350 (千位逗号)"""
    s = s.strip().replace('，', ',').replace('．', '.')
    if ',' in s:
        parts = s.split(',')
        if len(parts) == 2 and len(parts[1]) in (1, 2):
            s = s.replace(',', '.')
        elif len(parts) == 2 and len(parts[1]) == 3:
            s = s.replace(',', '')
        else:
            s = ''.join(parts)
    try:
        f = float(s)
    except ValueError:
        return None
    if abs(f - round(f)) < 1e-9:
        return int(round(f))
    return round(f, 3)


def in_range(param, v):
    if param not in RANGES:
        return True
    lo, hi = RANGES[param]
    return lo <= v <= hi


# ---------------------------------------------------------------- 文本采集

def collect_pdf(path):
    """返回 items: [{t, x0, y0, x1, y1, page}] + 页文本 {page: str}"""
    import fitz
    items, pagetext = [], {}
    d = fitz.open(path)
    for pno in range(len(d)):
        words = d[pno].get_text("words")
        for w in words:
            t = w[4].strip()
            if t:
                items.append({'t': t, 'x0': w[0], 'y0': w[1], 'x1': w[2], 'y1': w[3],
                              'page': pno + 1})
        pagetext[pno + 1] = d[pno].get_text()
    d.close()
    return items, pagetext


def _clean_mtext(s):
    s = s.replace('\\P', '\n').replace('\\p', '\n')
    s = re.sub(r'\\[A-Za-z][^;\\]*;', '', s)      # \fSimSun; \H2.5x; \A1; ...
    s = s.replace('{', '').replace('}', '')
    return s


def collect_dxf(path):
    """原始标记流扫描 TEXT/MTEXT/DIMENSION/ATTRIB 文本（无需 CAD 软件）"""
    raw = open(path, 'rb').read()
    try:
        text = raw.decode('utf-8')
        if '\\U+' in text:  # 某些 CAD 用 \U+XXXX 转义中文
            pass
    except UnicodeDecodeError:
        text = raw.decode('gbk', errors='replace')

    lines = text.splitlines()
    items = []
    cur, chunks, pos = None, [], None

    def flush():
        nonlocal cur, chunks, pos
        if cur and chunks:
            if cur == 'MTEXT':
                parts = [v for c, v in chunks if c == '3'] + \
                        [v for c, v in chunks if c == '1']
                full = _clean_mtext(''.join(parts))
            else:
                full = _clean_mtext(chunks[-1][1] if chunks[-1][0] == '1' else '')
            for seg in full.split('\n'):
                seg = seg.strip()
                if seg:
                    x = float(pos[0]) if pos and len(pos) == 2 else 0.0
                    y = float(pos[1]) if pos and len(pos) == 2 else 0.0
                    items.append({'t': seg, 'x0': x, 'y0': y, 'x1': x, 'y1': y,
                                  'page': 0})
        cur, chunks, pos = None, [], None

    i = 0
    n = len(lines)
    while i + 1 < n:
        code = lines[i].strip()
        val = lines[i + 1].rstrip('\r')
        i += 2
        if code == '0':
            flush()
            cur = val.strip().upper()
        elif cur in ('TEXT', 'MTEXT', 'DIMENSION', 'ATTRIB', 'ATTDEF'):
            if code == '1':
                chunks.append(('1', val))
            elif code == '3' and cur == 'MTEXT':
                chunks.append(('3', val))
            elif code == '10' and pos is None:
                pos = [val]
            elif code == '20' and pos is not None and len(pos) == 1:
                pos.append(val)
    flush()

    # 兜底: 逐行文本扫描（应对扫描器漏掉的实体）
    pagetext = {0: ' '.join(it['t'] for it in items)}
    return items, pagetext


# ---------------------------------------------------------------- 匹配层

def add_candidate(result, param, value, page, ev, score, tag=None):
    v = norm_num(str(value))
    if v is None or not in_range(param, v):
        return
    lst = result.setdefault(param, [])
    for c in lst:
        if c['v'] == v:
            c['count'] += 1
            if score > c['score']:
                c['score'], c['ev'], c['page'], c['tag'] = score, ev, page, tag
            return
    lst.append({'v': v, 'page': page, 'ev': ev, 'score': score, 'count': 1,
                'tag': tag})


def tier1_tokens(result, items):
    """层1: 单 token 内 KEY=value / 中文标注=值"""
    pat_latin = re.compile(
        r'^\s*([A-Za-z]{1,4}[A-Za-z0-9_]*)\s*=\s*' + NUM_RE + r'\s*(?:mm|MM)?\s*$')
    pat_desc = re.compile(
        r'^\s*(CA|CB|CH|RH|PL|LH|JJ|HH|SW|EA|FT)\s*[（(].*?[）)]?\s*[:=：]?\s*' +
        NUM_RE)
    pat_cn = re.compile(
        r'^\s*(' + '|'.join(CN_LABELS) + r')\s*(?:\(kg\)|（kg）)?\s*[:=：]?\s*' + NUM_RE,
        re.I)
    for it in items:
        t = it['t']
        m = pat_latin.match(t)
        if m:
            param = KEY_ALIAS.get(m.group(1).upper())
            if param:
                add_candidate(result, param, m.group(2), it['page'],
                              t, 100)
                continue
        m = pat_desc.match(t)
        if m:
            param = KEY_ALIAS.get(m.group(1).upper())
            if param:
                add_candidate(result, param, m.group(2), it['page'], t, 95)
                continue
        m = pat_cn.match(t)
        if m:
            param = CN_LABELS.get(m.group(1))
            if param:
                add_candidate(result, param, m.group(2), it['page'], t, 95)


def tier1b_same_line(result, items):
    """层1b: 标签 token（如 CA（CAR WIDTH）/ 轿厢宽度）后同行最近数值"""
    by_page = {}
    for it in items:
        by_page.setdefault(it['page'], []).append(it)
    pat_label = re.compile(
        r'^\s*(CA|CB|CH|RH|PL|LH|JJ|HH|SW|EA|FT)\s*[（(]')
    pat_cn_label = re.compile(r'^\s*(' + '|'.join(CN_LABELS) + r')\s*[:=：]?\s*$')
    num_pat = re.compile(r'^[-+]?\d+(?:[.,]\d+)?$')
    for page, its in by_page.items():
        for it in its:
            t = it['t']
            m = pat_label.match(t)
            param = KEY_ALIAS.get(m.group(1).upper()) if m else None
            if not param:
                mc = pat_cn_label.match(t)
                param = CN_LABELS.get(mc.group(1)) if mc else None
            if not param:
                continue
            yc = (it['y0'] + it['y1']) / 2
            tol = max(6.0, (it['y1'] - it['y0']) * 0.9)
            best = None
            for o in its:
                if o is it:
                    continue
                if not num_pat.match(o['t']):
                    continue
                oyc = (o['y0'] + o['y1']) / 2
                if abs(oyc - yc) > tol:
                    continue
                dist = o['x0'] - it['x1']
                if dist < -2 or dist > 250:
                    continue
                if best is None or dist < best[0]:
                    best = (dist, o)
            if best:
                ev = t + ' ' + best[1]['t']
                add_candidate(result, param, best[1]['t'], page, ev, 90)


def tier2_phrases(result, pagetext):
    """层2: 页文本短语匹配（英文图纸 / 规格表）"""
    num = NUM_RE
    phrases = [
        (r'CAR\s+NET\s+HEIGHT\s*[:=：]?\s*' + num, 'CH', 75),
        (r'CAR\s+OVERALL\s+HEIGHT\s*[:=：]?\s*' + num, 'CH', 65),
        (r'CAR\s+INTERNAL\s*[:=：]?\s*' + num, 'car_internal', 70),
        (r'CAR\s+WIDTH\s*[:=：]?\s*' + num, 'CA', 55),
        (r'CAR\s+DEPTH\s*[:=：]?\s*' + num, 'CB', 55),
        (r'CAR\s+CLEAR\s+HEIGHT\s*[:=：]?\s*' + num, 'CH', 70),
        (r'CAPACITY\s*[:：]?\s*' + num + r'\s*(?:KG|KGS|KG\.)', 'capacity', 80),
        (r'RATED\s+LOAD\s*[:=：]?\s*' + num + r'\s*(?:KG|KGS)?', 'capacity', 75),
        (r'RATED\s+SPEED\s*[:=：]?\s*' + num, 'speed', 75),
        (r'\b' + num + r'\s*M\s*/\s*S\b', 'speed', 60),
        (r'DOOR\s+WIDTH\s*[:=：]?\s*' + num, 'JJ', 70),
        (r'DOOR\s+HEIGHT\s*[:=：]?\s*' + num, 'HH', 70),
        (r'CLEAR\s+OPENING\s*[:=：]?\s*' + num, 'JJ', 72),
        (r'ELEVATOR\s+MODEL\s*[:=：]\s*([A-Z0-9][A-Z0-9\- ]{1,40})', 'elevatorModel', 80),
        (r'CENTER(?:ING)?\s+OPENING|CENTRE(?:ING)?\s+OPENING|中分', 'openingType:center', 70),
        (r'SIDE\s+OPENING|旁开|TWO[\s\-]?SPEED\s+SIDE', 'openingType:side', 70),
    ]
    for page, txt in pagetext.items():
        flat = re.sub(r'\s+', ' ', txt)
        for pat, param, score in phrases:
            for m in re.finditer(pat, flat, re.I):
                if param == 'car_internal':
                    add_candidate(result, 'CA', m.group(1), page,
                                  'CAR INTERNAL ' + m.group(1), score,
                                  tag='CAR INTERNAL（宽/深需人工区分）')
                    add_candidate(result, 'CB', m.group(1), page,
                                  'CAR INTERNAL ' + m.group(1), score,
                                  tag='CAR INTERNAL（宽/深需人工区分）')
                elif param == 'openingType:center':
                    add_candidate(result, 'openingType', '中分', page,
                                  m.group(0), score)
                elif param == 'openingType:side':
                    add_candidate(result, 'openingType', '旁开', page,
                                  m.group(0), score)
                elif param == 'elevatorModel':
                    val = m.group(1).strip()
                    # 截断到下一个明显非型号词
                    val = re.split(r'\s+(?:DATE|SCALE|UNIT|CAPACITY|PROJECT)\b',
                                   val)[0].strip()
                    add_candidate(result, param, val, page, m.group(0), score,
                                  tag='text')
                else:
                    add_candidate(result, param, m.group(1), page,
                                  m.group(0), score)
        # OPENING（排除 CONCRETE OPENING）
        for m in re.finditer(r'OPENING\s*[:=：]?\s*' + num, flat, re.I):
            before = flat[max(0, m.start() - 14):m.start()]
            if 'CONCRETE' in before.upper():
                continue
            add_candidate(result, 'JJ', m.group(1), page, m.group(0), 65)


# ---------------------------------------------------------------- 主流程

def main():
    if len(sys.argv) < 2:
        print(MARKER)
        print(json.dumps({'ok': False, 'error': 'missing file argument'},
                         ensure_ascii=False))
        return
    path = sys.argv[1]
    ext = os.path.splitext(path)[1].lower()
    if not os.path.exists(path):
        out = {'ok': False, 'error': '文件不存在: %s' % path}
    elif ext == '.pdf':
        items, pagetext = collect_pdf(path)
        result = {}
        tier1_tokens(result, items)
        tier1b_same_line(result, items)
        tier2_phrases(result, pagetext)
        pages = max(pagetext) if pagetext else 0
        out = {'ok': True, 'kind': 'pdf', 'file': os.path.basename(path),
               'pages': pages, 'params': result}
    elif ext == '.dxf':
        items, pagetext = collect_dxf(path)
        result = {}
        tier1_tokens(result, items)
        tier1b_same_line(result, items)
        tier2_phrases(result, pagetext)
        out = {'ok': True, 'kind': 'dxf', 'file': os.path.basename(path),
               'pages': 0, 'params': result}
    else:
        out = {'ok': False, 'error': '不支持的文件类型: %s（仅支持 PDF/DXF）' % ext}

    # 每个参数按 score 降序
    if out.get('ok'):
        for k in out['params']:
            out['params'][k].sort(key=lambda c: (-c['score'], -c['count']))

    print(MARKER)
    print(json.dumps(out, ensure_ascii=False))


if __name__ == '__main__':
    main()
