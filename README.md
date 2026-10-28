# IKOVOX 매장 인사이트

빌드 없이 실행하는 비공개 매출·PM 운영 대시보드. `dist/`를 정적 서버로 제공합니다.

- 매출: Drive 일별매출입력에서 이코복스 행만 추출. 조회일 2026-10-28. 118일, 2026-07-01~10-26.
- 상품: 기존 베이커리·젤라또 내부 HTML 리포트 7~9월. 매장 판매 기준을 유지.
- 수정·입력·목표·체크리스트: 브라우저 localStorage. 데이터 관리에서 JSON 백업·복원.
- 자동 동기화·팀 공동 편집·서버 저장소는 미연결.
- 모든 외부 입력은 HTML escape. CSV 전체 검증 후 반영. 중복 날짜는 확인 후 교체.

## 실행

`python3 -m http.server 4173 --directory dist --bind 127.0.0.1`

`pm-guide.md`, `weekly-report.md`는 웹에서도 내려받을 수 있습니다.

## Calendar update

`dist/sales-view.js` owns the weekly/monthly calendar, date/range detail routes, comparison and coverage logic, product/category filters, weekly menu analysis, hourly CSV import, and operational insights. Deep links use `#dashboard?from=YYYY-MM-DD&to=YYYY-MM-DD&tab=trend` (tabs: trend/time/products/menus/insights). `analysis-data.json` contains 2026-08 and 2025-10 POS product records and explicit day coverage. No time-series product data is synthesized from monthly reports. Local uploads replace whole covered dates, after complete CSV validation. Missing data is never filled with zero. Browser backups include analysis uploads and menu settings.
