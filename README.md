# IKOVOX 매장 인사이트

이코복스 매출·PM 운영 대시보드. 기존 화면 소스와 데이터는 `public/`, 재료·레시피 공유 API는 `server/cost-api.js`에서 관리합니다. Sites의 Worker와 D1 데이터베이스를 사용합니다.

- 매출: Drive 일별매출입력에서 이코복스 행만 추출. 조회일 2026-10-28. 118일, 2026-07-01~10-26.
- 상품: 기존 베이커리·젤라또 내부 HTML 리포트 7~9월. 매장 판매 기준을 유지.
- 수정·입력·목표·체크리스트: 브라우저 localStorage. 데이터 관리에서 JSON 백업·복원.
- 재료·레시피는 공용 관리 비밀번호로 로그인한 기기끼리 D1 서버 자료를 공유합니다. 다른 업무 입력은 브라우저 저장을 유지합니다.
- 메뉴 원가 관리(`#costs`): 재료·포장재 매입단가, kg/L 단위 환산, 사용 가능 비율, 배합별 사용량 및 판매 가능 수량으로 개당 원가·원가율 계산. 단가 수정 시 연결 메뉴에 즉시 반영. 실제 레시피는 초기 제공하지 않으며 직접 등록합니다.
- 기존 `ikovox:costs` 브라우저 자료는 서버가 비어 있을 때 로그인 후 명시적으로 옮길 수 있습니다. 서버 저장 시 버전 충돌과 빈 자료 덮어쓰기를 차단하며 이전 버전을 D1에 자동 보관합니다. API는 비밀번호 로그인·HttpOnly 쿠키로 보호합니다. 실제 자료와 비밀번호는 GitHub 소스에 넣지 않습니다.
- 모든 외부 입력은 HTML escape. CSV 전체 검증 후 반영. 중복 날짜는 확인 후 교체.

## 실행

`npm ci` 후 `npm run build`, 로컬 D1 마이그레이션 적용, `npm run start` 순서로 실행합니다. 개발 서버는 `npm run dev`입니다.

Sites 환경 변수 `COST_PASSWORD_HASH`(관리 비밀번호의 SHA-256)와 `COST_SESSION_SECRET`(충분히 긴 무작위 문자열)을 secret으로 설정합니다. 로컬 테스트 설정은 Git에서 제외한 `.dev.vars`에 보관합니다. `.openai/hosting.json`은 D1 바인딩 `DB`를 선언합니다.

`pm-guide.md`, `weekly-report.md`는 웹에서도 내려받을 수 있습니다.

## 소스와 입력 자료 보관

GitHub에는 홈페이지 소스, 배포에 사용하는 매출 스냅샷, 검증·갱신 스크립트를 보관합니다. 내려받은 원가·업무 백업 파일과 인증정보는 커밋하지 않습니다.

서버의 재료·레시피는 D1에 저장되고 Git 저장소에 자동 반영되지 않습니다. 공용 비밀번호를 아는 사람은 같은 자료를 조회·수정할 수 있습니다. 매출 수정·목표·체크리스트 등 다른 업무 입력은 여전히 브라우저 저장이며, JSON 백업 파일은 별도로 보관할 수 있습니다.

원가 계산 검증: `node scripts/check_costs.mjs`

공유 저장 검증: `node scripts/check_shared_costs.mjs` (Node.js 24 이상)

## Calendar update

`dist/sales-view.js` owns the weekly/monthly calendar, date/range detail routes, comparison and coverage logic, product/category filters, weekly menu analysis, hourly CSV import, and operational insights. Deep links use `#dashboard?from=YYYY-MM-DD&to=YYYY-MM-DD&tab=trend` (tabs: trend/time/products/menus/insights). `analysis-data.json` contains 2026-08 and 2025-10 POS product records and explicit day coverage. No time-series product data is synthesized from monthly reports. Local uploads replace whole covered dates, after complete CSV validation. Missing data is never filled with zero. Browser backups include analysis uploads and menu settings.
