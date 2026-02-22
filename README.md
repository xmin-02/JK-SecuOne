# JK SecuOne

**Security Vulnerability Analysis Dashboard** — Upload Pentera or SentinelOne reports, automatically extract vulnerabilities via OCR, and map them to ISMS-P (Korea's Information Security Management System - Personal Information) certification controls.

## Overview

JK SecuOne is a web-based security compliance platform that bridges the gap between penetration testing / endpoint detection tools and ISMS-P audit requirements. Security teams upload PDF or CSV reports from Pentera or SentinelOne, and the system automatically:

1. Extracts vulnerability and threat data using multi-engine OCR (EasyOCR + Tesseract + PyMuPDF)
2. Maps each finding to relevant ISMS-P certification controls
3. Generates compliance status reports with mitigation rates per control
4. Tracks scan history per user with plan-based usage limits

## Architecture

```
Browser (Vanilla JS)
    |
    |  REST API (JSON)
    v
FastAPI Server (app.py, port 5050)
    |
    |--- Pentera Pipeline (pentera_ISMS_P.py)
    |       |-- PDF OCR: PyMuPDF + Tesseract
    |       |-- Achievements parser (regex-based)
    |       |-- Vulnerability-to-number mapping (pentera_Vulnerabilities.csv)
    |       |-- Number-to-ISMS-P mapping (ISMS_P.csv)
    |
    |--- SentinelOne Pipeline (sentinelOne_ISMS_P.py)
    |       |-- PDF OCR: EasyOCR (primary) + Tesseract (fallback)
    |       |-- CSV direct import
    |       |-- Threat classification parser (regex-based)
    |       |-- Built-in ISMS-P control mapping (hardcoded)
    |
    |--- SQLite (users.db)
            |-- users table (auth, plans)
            |-- scan_history table (results archive)
```

## Features

### Report Analysis
- **Pentera**: Upload PDF reports. The system finds the Table of Contents, locates the "Achievements" section, extracts vulnerability entries (#number, severity, name) across multiple pages, then maps each to ISMS-P controls via two-stage CSV lookup.
- **SentinelOne**: Upload PDF or CSV reports. PDFs are processed with EasyOCR (Korean + English) for threat count, mitigation status, classifications (Malware, Ransomware, Trojan, Suspicious, PUP), and device information. CSV files are parsed directly. Each threat classification maps to predefined ISMS-P controls.

### ISMS-P Mapping
- **Pentera**: Uses a two-file mapping chain: `pentera_Vulnerabilities.csv` (vulnerability name -> #number) -> `ISMS_P.csv` (#number -> ISMS-P controls with category, criteria, and compliance details)
- **SentinelOne**: Uses a built-in mapping table that links threat classifications to ISMS-P control codes (2.7.1 Incident Prevention, 2.8.4 Malware Control, 2.3.3 Access Management, etc.)

### User Management
- Signup with email verification (Gmail SMTP with 6-digit code, 10-minute expiry)
- Login with SHA-256 password hashing
- Profile management (name, username, phone, email change with re-verification, password change)
- Password recovery via email
- Account deletion

### Plan System
| Plan | SentinelOne Scans | Pentera Scans |
|------|-------------------|---------------|
| Free | 10 | 1 |
| Sentinel One + | Unlimited | 2 |
| Pentera + | 20 | Unlimited |
| Premium + | Unlimited | Unlimited |

### Admin Panel
- User management (view all, change plans, delete users)
- Scan statistics dashboard
- Per-user scan history reset

### Scan History
- Automatic save on each analysis
- Deduplication by filename (shows latest only)
- Soft delete support
- Full usage history (including deleted records)
- Detailed result retrieval for past scans

## Tech Stack

### Backend
| Component | Technology | Purpose |
|-----------|-----------|---------|
| Web Framework | **FastAPI** + Uvicorn | Async HTTP server, auto API docs at `/docs` |
| Database | **SQLite3** | User accounts, scan history storage |
| PDF Processing | **PyMuPDF** (fitz) | PDF page rendering to images, text layer extraction |
| OCR Engine 1 | **EasyOCR** | Primary OCR for Korean + English (GPU optional) |
| OCR Engine 2 | **Tesseract** (pytesseract) | Fallback OCR engine |
| PDF Reader | **PyPDF2** | Native text extraction before OCR fallback |
| Image Processing | **Pillow** (PIL) | Image format conversion for OCR |
| Email | **smtplib** | Gmail SMTP for verification codes |
| Auth | **hashlib** (SHA-256) | Password hashing |

### Frontend
| Component | Technology | Purpose |
|-----------|-----------|---------|
| UI | **Vanilla HTML/CSS/JS** | No framework dependency |
| Styling | Custom CSS with CSS Variables | Dark theme, responsive design |
| File Upload | Drag & Drop + File Input | PDF/CSV upload with type validation |
| State | **localStorage** | Client-side session management |
| API Communication | **Fetch API** | REST calls to backend |

### Data Files
| File | Format | Purpose |
|------|--------|---------|
| `ISMS_P.csv` | CSV (UTF-8/CP949) | ISMS-P certification criteria with Pentera number mapping |
| `pentera_Vulnerabilities.csv` | CSV | 41 vulnerability names mapped to Pentera achievement numbers |

## Project Structure

```
JK/
├── app.py                          # FastAPI main server (1,666 lines)
├── pentera_ISMS_P.py               # Pentera PDF extraction + ISMS-P mapping (611 lines)
├── sentinelOne_ISMS_P.py           # SentinelOne analysis pipeline (984 lines)
├── requirements.txt                # Python dependencies
├── ISMS_P.csv                      # ISMS-P certification criteria data
├── pentera_Vulnerabilities.csv     # Pentera vulnerability-to-number mapping
├── static/
│   ├── css/
│   │   └── style.css               # Global styles with CSS variables
│   ├── images/
│   │   ├── JK SecuOne_logo.png     # Platform logo
│   │   ├── Pentera_logo.png        # Pentera tool logo
│   │   └── SentinelOne_logo.png    # SentinelOne tool logo
│   └── js/
│       ├── main.js                 # Dashboard logic (file upload, analysis, results display)
│       ├── mypage.js               # Profile, admin panel, scan history, pricing
│       └── signup.js               # Signup form validation, email verification
├── templates/
│   ├── dashboard.html              # Main dashboard (tool selection, upload, results)
│   ├── login.html                  # Login page
│   ├── signup.html                 # Registration page
│   ├── forgot_password.html        # Password recovery (3-step flow)
│   └── mypage.html                 # User profile, admin, pricing, scan history
└── .gitignore
```

## Setup

### Prerequisites
- Python 3.8+
- Tesseract OCR (optional, EasyOCR is the primary engine)

### Installation

```bash
pip install -r requirements.txt
```

### Run

```bash
python app.py
```

The server starts at `http://localhost:5050`. API documentation is available at `http://localhost:5050/docs`.

## API Endpoints

### Analysis
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/analyze/pentera` | Analyze Pentera PDF report |
| POST | `/api/analyze/sentinelone` | Analyze SentinelOne PDF/CSV report |

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/signup` | User registration |
| POST | `/api/auth/login` | User login |
| POST | `/api/auth/send-verification` | Send email verification code |
| POST | `/api/auth/verify-code` | Verify email code |
| POST | `/api/auth/verify-email` | Verify email for password recovery |
| POST | `/api/auth/reset-password` | Reset password |

### User
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/user/profile/{user_id}` | Get user profile |
| PUT | `/api/user/update-basic` | Update name, username, phone |
| PUT | `/api/user/update-email` | Update email (with verification) |
| PUT | `/api/user/update-password` | Update password (with verification) |
| PUT | `/api/user/change-plan` | Change subscription plan |
| DELETE | `/api/user/delete-account` | Delete account |

### Scan History
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/scan/save` | Save scan result |
| GET | `/api/scan/history/{user_id}` | Get scan history (deduplicated) |
| GET | `/api/scan/usage-history/{user_id}` | Get full usage history |
| GET | `/api/scan/detail/{scan_id}` | Get scan details |
| DELETE | `/api/scan/delete/{scan_id}` | Soft-delete scan |

### Admin
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/admin/stats` | Dashboard statistics |
| GET | `/api/admin/users` | List all users |
| PUT | `/api/admin/user/{id}/plan` | Change user plan |
| DELETE | `/api/admin/user/{id}` | Delete user |
| DELETE | `/api/admin/user/{id}/clear-scans` | Clear user's scan history |

---

# JK SecuOne (한국어)

**보안 취약점 분석 대시보드** — Pentera 또는 SentinelOne 보고서를 업로드하면, OCR로 취약점을 자동 추출하고 ISMS-P 인증기준에 매핑합니다.

## 개요

JK SecuOne은 모의해킹(Pentera) 및 엔드포인트 탐지(SentinelOne) 도구의 보고서를 ISMS-P 감사 요구사항과 연결하는 웹 기반 보안 컴플라이언스 플랫폼입니다.

**동작 흐름:**
1. 사용자가 Pentera PDF 또는 SentinelOne PDF/CSV 보고서를 업로드
2. 다중 OCR 엔진(EasyOCR + Tesseract + PyMuPDF)으로 취약점/위협 데이터 추출
3. 추출된 각 항목을 ISMS-P 인증기준에 자동 매핑
4. 인증기준별 조치율을 포함한 준수 현황 보고서 생성
5. 사용자별 검사 이력을 플랜 기반 사용 한도와 함께 관리

## 주요 기능

### 보고서 분석
- **Pentera 분석**: PDF 보고서에서 목차(Table of Contents)를 찾고, Achievements 섹션의 취약점 항목(번호, 심각도, 이름)을 다중 페이지에 걸쳐 추출. 2단계 CSV 매핑으로 ISMS-P 연결
- **SentinelOne 분석**: PDF는 EasyOCR(한국어+영어)로 위협 수, 조치 상태, 분류(Malware/Ransomware/Trojan 등), 기기 정보 파싱. CSV는 직접 파싱. 위협 분류별로 사전 정의된 ISMS-P 통제 항목에 매핑

### ISMS-P 매핑 방식
- **Pentera**: 2단계 CSV 매핑 체인
  - `pentera_Vulnerabilities.csv`: 취약점명 -> #번호 (41개 취약점 정의)
  - `ISMS_P.csv`: #번호 -> ISMS-P 인증기준 (분류, 항목, 인증기준, 주요 확인사항, 관련 법규, 미흡사례)
- **SentinelOne**: 내장 매핑 테이블
  - Malware -> 2.8.4(악성코드 통제), 2.7.1(침해사고 예방), 2.7.2(대응/복구)
  - Ransomware -> 위 항목 + 2.11.1(백업/복구), 2.9.1(암호정책)
  - Trojan -> 2.8.4, 2.8.5(침입 탐지/차단), 2.3.3(접근 관리), 2.7.2
  - 등 6개 분류별 매핑

### 사용자 관리
- 이메일 인증 회원가입 (Gmail SMTP, 6자리 인증코드, 10분 유효)
- SHA-256 비밀번호 해싱 기반 로그인
- 프로필 관리 (이름, 아이디, 연락처, 이메일 변경 시 재인증, 비밀번호 변경)
- 이메일 기반 비밀번호 찾기 (3단계: 아이디+이메일 확인 -> 인증코드 -> 재설정)
- 회원 탈퇴

### 요금제
| 플랜 | SentinelOne 검사 | Pentera 검사 |
|------|------------------|--------------|
| 무료 | 10회 | 1회 |
| Sentinel One + | 무제한 | 2회 |
| Pentera + | 20회 | 무제한 |
| Premium + | 무제한 | 무제한 |

### 관리자 기능
- 전체 사용자 목록 조회 및 관리
- 사용자별 플랜 변경, 계정 삭제
- 검사 통계 대시보드
- 사용자별 검사 내역 초기화

### 검사 이력
- 분석 완료 시 자동 저장
- 동일 파일명 중복 제거 (최신 것만 표시)
- 소프트 삭제 지원 (사용 내역에는 유지)
- 상세 결과 재조회 가능

## 기술 스택

### 백엔드
| 구성요소 | 기술 | 용도 |
|---------|------|------|
| 웹 프레임워크 | **FastAPI** + Uvicorn | 비동기 HTTP 서버, `/docs`에서 API 문서 자동 생성 |
| 데이터베이스 | **SQLite3** | 사용자 계정, 검사 이력 저장 |
| PDF 처리 | **PyMuPDF** (fitz) | PDF 페이지를 이미지로 렌더링, 텍스트 레이어 추출 |
| OCR 엔진 1 | **EasyOCR** | 한국어+영어 주력 OCR (GPU 선택) |
| OCR 엔진 2 | **Tesseract** (pytesseract) | 폴백 OCR 엔진 |
| PDF 리더 | **PyPDF2** | OCR 전 네이티브 텍스트 추출 시도 |
| 이미지 처리 | **Pillow** (PIL) | OCR용 이미지 포맷 변환 |
| 이메일 | **smtplib** | Gmail SMTP 인증코드 발송 |
| 인증 | **hashlib** (SHA-256) | 비밀번호 해싱 |

### 프론트엔드
| 구성요소 | 기술 | 용도 |
|---------|------|------|
| UI | **순수 HTML/CSS/JS** | 프레임워크 없이 구현 |
| 스타일링 | CSS Variables 기반 커스텀 CSS | 다크 테마, 반응형 디자인 |
| 파일 업로드 | 드래그 앤 드롭 + 파일 입력 | PDF/CSV 업로드 (타입 검증 포함) |
| 상태 관리 | **localStorage** | 클라이언트 측 세션 관리 |
| API 통신 | **Fetch API** | 백엔드 REST 호출 |

## 프로젝트 구조

```
JK/
├── app.py                          # FastAPI 메인 서버 (1,666줄)
│                                     - 라우트: /, /login, /signup, /forgot-password, /mypage
│                                     - API: 분석, 인증, 사용자, 스캔이력, 관리자
│                                     - SQLite DB 초기화 및 관리
├── pentera_ISMS_P.py               # Pentera 분석 파이프라인 (611줄)
│                                     - PenteraPDFExtractor: PDF OCR 추출
│                                     - ISMSPMapper: 취약점 -> ISMS-P 매핑
├── sentinelOne_ISMS_P.py           # SentinelOne 분석 파이프라인 (984줄)
│                                     - pdf_to_ocr_json: PDF -> OCR JSON 변환
│                                     - 위협 파싱 (수, 분류, 기기, 조치 상태)
│                                     - ISMS-P 통제 항목 매핑 및 감사 보고서 생성
├── requirements.txt                # Python 의존성
├── ISMS_P.csv                      # ISMS-P 인증기준 데이터
├── pentera_Vulnerabilities.csv     # Pentera 취약점-번호 매핑 (41개)
├── static/
│   ├── css/style.css               # 전역 스타일 (CSS 변수 기반 다크 테마)
│   ├── images/                     # 로고 이미지 (JK SecuOne, Pentera, SentinelOne)
│   └── js/
│       ├── main.js                 # 대시보드 (도구 선택, 파일 업로드, 분석, 결과 표시, 플랜 한도 체크)
│       ├── mypage.js               # 마이페이지 (프로필, 관리자, 검사 이력, 요금제)
│       └── signup.js               # 회원가입 (폼 검증, 연락처 포맷팅, 비밀번호 강도, 이메일 인증)
└── templates/
    ├── dashboard.html              # 메인 대시보드
    ├── login.html                  # 로그인
    ├── signup.html                 # 회원가입
    ├── forgot_password.html        # 비밀번호 찾기 (3단계)
    └── mypage.html                 # 마이페이지 (프로필/관리자/요금제/검사이력/정보수정/설정)
```

## 설치 및 실행

### 필수 요건
- Python 3.8+
- Tesseract OCR (선택 - EasyOCR이 주력 엔진)

### 설치

```bash
pip install -r requirements.txt
```

### 실행

```bash
python app.py
```

서버가 `http://localhost:5050`에서 시작됩니다. API 문서는 `http://localhost:5050/docs`에서 확인할 수 있습니다.
