[AI 도어캠 상세페이지 - 수정본 (FAQ·표·하단정보 깨짐 해결)]

■ 무엇이 바뀌었나
- FAQ / 제품 상세정보 표 / 하단 제품정보 → 오버레이 텍스트를 '진짜 HTML'로 교체
  (자동 줄바꿈 → 겹침·넘침 없음, 모바일에서도 안전)
- 안심보상·구성품·각부설명 = 이미지(blk_ansim/blk_comp/blk_parts)
- 마케팅 섹션(사진 위 헤드라인)은 기존과 동일

■ 적용 방법 (카페24)
1) images 폴더의 새 이미지 3장 업로드: blk_ansim.jpg, blk_comp.jpg, blk_parts.jpg
   (기존 bg_01~bg_24 는 그대로 사용, bg_25~bg_29 는 더 이상 사용 안 함 → 삭제 가능)
2) index.html 의 src="images/..." 경로를 기존처럼 서버 URL로 일괄 변경
   (예: images/  →  //ecimg.cafe24img.com/.../doorcam/ )
3) 상세 편집 HTML 모드에 index.html 내용 붙여넣기 (기존 것과 교체)

※ 새로 추가된 <style> 안의 .dcx-* 규칙이 FAQ/표/푸터 서식입니다. 통째로 붙여넣으면 됩니다.
