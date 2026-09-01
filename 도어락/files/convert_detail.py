#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
카페24 상품 상세설명 변환기 (v3.1)

.safe 템플릿으로 작성된 상세페이지 HTML을
카페24 상품 상세설명에 그대로 붙여넣을 수 있는 형태로 변환한다.

핵심: 반응 기준을 '화면 폭(@media)' → '컬럼 폭(@container)'으로 전환.
      카페24 product/detail.html 에는 <head>가 없어 viewport 메타를 쓸 수 없으므로,
      뷰포트에 의존하지 않는 구조여야 한다.

사용법:
    python3 convert_detail.py <입력.html> <출력디렉터리> [--name "상품명"] [--code "SFS10054"]
    python3 convert_detail.py doorlock_a.html out/DOORLOCK_A --name "도어락 A" --code SFS10054
"""
import re, os, sys, base64, argparse

REF = 780.0  # 이 컨테이너 폭에서 원본 px 그대로. 그 이하에서 비례 축소.

IMG_PROPS = ('max-width', 'min-width', 'width', 'height', 'max-height',
             'position', 'object-fit', 'left', 'top', 'right', 'bottom', 'inset')


# ─────────────────────────────────────────────────────────── helpers
def split_blocks(css):
    """최상위 @media 블록을 분리해 (본문, [(조건, 내용), ...]) 반환."""
    out, medias, i = [], [], 0
    while i < len(css):
        m = re.compile(r'@media\s*([^{]+)\{').search(css, i)
        if not m:
            out.append(css[i:]); break
        out.append(css[i:m.start()])
        depth, j = 1, m.end()
        while j < len(css) and depth:
            if css[j] == '{': depth += 1
            elif css[j] == '}': depth -= 1
            j += 1
        medias.append((m.group(1).strip(), css[m.end():j - 1]))
        out.append('\n/*__MEDIA_%d__*/\n' % (len(medias) - 1))
        i = j
    return ''.join(out), medias


def fluid_fontsize(css):
    """font-size:Npx → 폴백 px + clamp(min, K cqi, Npx)

    구형 브라우저는 앞의 px를, cqi 지원 브라우저는 clamp를 사용한다.
    """
    def rep(m):
        n = float(m.group(1))
        if n >= 24:   lo = round(n * 0.74, 1)   # 제목류: 크게 축소 허용
        elif n >= 16: lo = round(n * 0.88, 1)   # 본문류: 약간만
        else:         lo = round(max(n * 0.92, 10.5), 1)  # 캡션류: 하한 10.5px
        k = round(n / REF * 100, 2)
        return 'font-size:%gpx;font-size:clamp(%gpx,%gcqi,%gpx)' % (n, lo, k, n)
    return re.sub(r'font-size:\s*([0-9]+(?:\.[0-9]+)?)px', rep, css)


def img_cap_rules(css, img_classes):
    """<img>에 쓰인 클래스의 크기/위치 선언을 !important로 재선언.

    방어 규칙의 `.lucell img{max-width:100% !important}` 에
    개별 최대폭(.hero-img{max-width:420px} 등)이 덮이는 것을 막는다.
    """
    rules, seen = [], set()
    for sel, body in re.findall(r'([^{}]+)\{([^{}]*)\}', css):
        sel = sel.strip()
        if sel.startswith('@') or not sel:
            continue
        if not any('.' + c in sel for c in img_classes):
            continue
        decls = []
        for d in body.split(';'):
            if ':' not in d:
                continue
            if d.split(':', 1)[0].strip() in IMG_PROPS:
                decls.append(d.strip().replace('!important', '').strip() + ' !important')
        if decls:
            key = (sel, tuple(decls))
            if key in seen:
                continue
            seen.add(key)
            rules.append('%s{%s;}' % (sel, ';'.join(decls)))
    return rules


DEFENSE = """
/* ═══════════════════════════════════════════════════════════════════
   [v3.1] 카페24 상세설명 대응 — 컨테이너 쿼리 전환 + 스킨 CSS 방어
   · 뷰포트(화면 폭)가 아니라 삽입된 컬럼 폭에 반응
   · 아래는 위 원본 CSS를 덮어쓰는 오버라이드 (선언 순서 유지 필수)
   ═══════════════════════════════════════════════════════════════════ */

/* 1) 컨테이너 선언 — 이 파일의 핵심 */
.lucell{
  container-type:inline-size;
  container-name:lud;
  display:block;
  width:100%;
  max-width:860px;
  margin:0 auto;
  font-size:16px;
  text-align:left;
  word-break:keep-all;
  overflow-wrap:anywhere;
  -webkit-text-size-adjust:100%;
  text-size-adjust:100%;
}

/* 2) 스킨 CSS 방어 */
.lucell *,.lucell *::before,.lucell *::after{box-sizing:border-box !important;}
.lucell *{font-family:inherit;}
.lucell img{display:block !important;max-width:100% !important;height:auto !important;border:0;}
.lucell table{width:100% !important;max-width:100% !important;border-collapse:collapse;background:none;}
.lucell p,.lucell li,.lucell h1,.lucell h2,.lucell h3,.lucell h4{
  word-break:keep-all;overflow-wrap:anywhere;}
/* 표 셀은 반드시 break-word.
   anywhere를 쓰면 min-content 폭이 1글자가 되어 열이 세로로 붕괴한다. */
.lucell th,.lucell td{word-break:keep-all;overflow-wrap:break-word;}
.lucell th{white-space:nowrap;}   /* 원본 동작 유지 — 좁은 컨테이너에서만 해제 */
.lucell ul,.lucell ol{list-style:none;}

/* 3) 아이콘 그리드 — 미디어쿼리 없이 폭에 따라 3열→2열→1열 */
.lucell .grid{
  display:grid !important;
  grid-template-columns:repeat(auto-fit,minmax(150px,1fr));
  gap:clamp(26px,4.5cqi,44px) clamp(10px,2cqi,20px);
  justify-content:center;
}
.lucell .feat{flex:initial;min-width:0;text-align:center;}
.lucell .feat svg{width:clamp(38px,6cqi,52px);height:clamp(38px,6cqi,52px);margin:0 auto 14px;display:block;}

/* 4) 썸네일 — 고정 % 폭 제거, 유동 배치 */
.lucell .thumbs{display:flex;flex-wrap:wrap;justify-content:center;}
.lucell .thumbs figure{flex:1 1 200px;width:auto;min-width:0;max-width:330px;}
.lucell .parts .thumbs figure{flex:1 1 130px;width:auto;min-width:0;max-width:200px;}
.lucell .holder .thumbs figure{flex:1 1 220px;width:auto;min-width:0;max-width:300px;}

/* 5) 콜아웃 다이어그램 */
.lucell .clabel{font-size:clamp(9.5px,1.6cqi,12.5px);white-space:normal;}
.lucell .art-diagram{max-width:100%;}
"""

CONTAINER_STEPS = """
/* 6) 컨테이너 폭별 여백/레이아웃 전환 (화면 폭 아님) */
@container lud (max-width:620px){
  .lucell .sec{padding:56px 22px;}
  .lucell .hero{padding:48px 22px 0;}
  .lucell .foot{padding:36px 22px;}
  .lucell .fire{padding-top:56px;}
  .lucell .fire .fire-txt{padding:0 22px;}
  .lucell .life .overlay{padding:24px 22px 26px;}
  .lucell .g-table th,.lucell .g-table td{padding:7px 4px;}
  .lucell table{table-layout:fixed;}
  .lucell th{white-space:normal;}
  .lucell .q{padding:14px 16px;}
  .lucell .a{padding:12px 16px 0;}
}
@container lud (max-width:460px){
  .lucell .sec{padding:44px 16px;}
  .lucell .hero{padding:40px 16px 0;}
  .lucell .foot{padding:30px 16px;}
  .lucell .fire .fire-txt{padding:0 16px;}
  .lucell .life .overlay{position:static;background:#1a1a1a;padding:22px 16px 26px;}
  .lucell .art-diagram{aspect-ratio:auto;}
}
@container lud (max-width:330px){
  .lucell .grid{grid-template-columns:1fr;}
}
"""

PRETENDARD = ("@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard"
              "@v1.3.9/dist/web/static/pretendard.min.css');")


# ─────────────────────────────────────────────────────────── main
def convert(src_path, out_dir, name=None, code=None):
    s = open(src_path, encoding='utf-8').read()
    m = re.search(r'<style[^>]*>(.*?)</style>', s, re.S)
    if not m:
        raise SystemExit('ERROR: <style> 블록을 찾을 수 없습니다: ' + src_path)
    css = m.group(1)
    b = re.search(r'<body[^>]*>(.*)</body>', s, re.S)
    body = b.group(1) if b else s

    if 'class="safe"' not in body:
        print('WARN: class="safe" 래퍼가 없습니다. 구조를 먼저 확인하세요:', src_path)

    os.makedirs(os.path.join(out_dir, 'images'), exist_ok=True)
    extracted = []

    # base64 인라인 이미지 → 파일로 분리 (카페24 용량/속도 대응)
    def dataurl_to_file(mm):
        mime, b64 = mm.group(1), mm.group(2)
        ext = {'image/jpeg': 'jpg', 'image/png': 'png', 'image/gif': 'gif',
               'image/webp': 'webp', 'image/svg+xml': 'svg'}.get(mime, 'bin')
        raw = base64.b64decode(b64)
        fn = 'img%02d.%s' % (len(extracted) + 1, ext)
        open(os.path.join(out_dir, 'images', fn), 'wb').write(raw)
        extracted.append(fn)
        return 'src="images/%s"' % fn

    body = re.sub(r'src="data:(image/[a-z+]+);base64,([^"]+)"', dataurl_to_file, body)

    # 클래스명 교체 (safe는 범용어라 스킨 CSS와 충돌 위험)
    css = css.replace('.safe', '.lucell')
    body = body.replace('class="safe"', 'class="lucell"')

    img_classes = set()
    for mm in re.finditer(r'<img[^>]*class="([^"]+)"', body):
        img_classes.update(mm.group(1).split())

    main, medias = split_blocks(css)
    caps = img_cap_rules(main, img_classes)
    main = fluid_fontsize(main)
    main = re.sub(r'/\*__MEDIA_\d+__\*/', '', main)

    cont = ['@container lud %s{%s}' % (c, i) for c, i in medias]
    fallback = ['@media %s{%s}' % (c, i) for c, i in medias]

    parts = [
        PRETENDARD,
        '\n/* ── 원본 디자인 CSS (색상·톤 유지, 폰트크기만 유동화) ── */',
        main.strip(),
        DEFENSE,
        '\n/* 7) 이미지 개별 크기·위치 캡 재선언 */',
        '\n'.join(caps),
        CONTAINER_STEPS,
        '\n/* 8) 원본 @media → @container 전환 */',
        '\n'.join(cont),
        '\n/* 9) 컨테이너 쿼리 미지원 브라우저 폴백 */',
        '@supports not (container-type:inline-size){\n' + '\n'.join(fallback) + '\n}',
    ]
    new_css = '\n'.join(p for p in parts if p.strip())

    label = '%s%s' % (name or os.path.basename(src_path), ' (%s)' % code if code else '')
    header = ("<!--\n  ============================================================\n"
              "  %s — 카페24 상품 상세설명 삽입용 [v3.1]\n"
              "  · 상세설명 에디터 [HTML] 소스 모드에 아래 전체를 붙여넣기\n"
              "  · images/ 경로는 웹FTP 업로드 후 실제 경로로 치환\n"
              "  · 저장 후 위지윅 모드로 재전환 금지 (style 태그 삭제됨)\n"
              "  ============================================================\n-->\n" % label)

    out_path = os.path.join(out_dir, 'index.html')
    open(out_path, 'w', encoding='utf-8').write(
        '<meta charset="UTF-8">\n' + header + '<style>\n' + new_css + '\n</style>\n' + body.strip() + '\n')

    # 자체 검증
    assert new_css.count('{') == new_css.count('}'), '중괄호 불균형'
    assert 'data:image' not in open(out_path, encoding='utf-8').read(), 'base64 잔존'
    assert 'class="safe"' not in body, 'safe 클래스 잔존'
    imgs = re.findall(r'<img[^>]*src="([^"]+)"', body)
    missing = [i for i in imgs if i.startswith('images/')
               and not os.path.exists(os.path.join(out_dir, i))]

    print('OK  %s' % out_path)
    print('    HTML %.1f KB / img태그 %d / base64추출 %d' %
          (os.path.getsize(out_path) / 1024, len(imgs), len(extracted)))
    if missing:
        print('    ! 이미지 누락(원본 images/ 폴더를 복사하세요):', missing)
    return out_path


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('out')
    ap.add_argument('--name', default=None)
    ap.add_argument('--code', default=None)
    a = ap.parse_args()
    convert(a.src, a.out, a.name, a.code)
