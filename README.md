# 🛡️ JK SecuOne - Security Vulnerability ISMS-P Mapping Dashboard

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg)
![EasyOCR](https://img.shields.io/badge/EasyOCR-1.7+-orange.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

**JK SecuOne** is a web-based security compliance platform that automatically extracts vulnerabilities from Pentera/SentinelOne reports via multi-engine OCR and maps them to ISMS-P certification controls.
Built with a FastAPI backend and vanilla JavaScript frontend.

---

## ✨ Key Features

### 🎯 Core
- **Pentera Report Analysis** — PDF OCR extraction of vulnerability achievements, mapped to ISMS-P via 2-stage CSV lookup
- **SentinelOne Report Analysis** — PDF/CSV threat parsing with classification-based ISMS-P control mapping
- **Multi-Engine OCR** — EasyOCR (Korean+English) primary, Tesseract fallback, PyMuPDF text layer extraction
- **ISMS-P Compliance Dashboard** — Per-control mitigation rates, violation status, and remediation guidance
- **Scan History** — Auto-save, deduplication, soft-delete, detailed result retrieval

### 👤 User Management
- **Email Verification Signup** — Gmail SMTP with 6-digit code (10-min expiry)
- **Plan-Based Usage Limits** — Free / Sentinel One+ / Pentera+ / Premium tiers
- **Admin Panel** — User management, plan changes, scan statistics, history reset
- **Password Recovery** — 3-step flow (identity verify → email code → reset)

### 🤖 Tech Stack
- **Backend**: FastAPI + Uvicorn, SQLite3
- **OCR Engines**: EasyOCR, Tesseract (pytesseract), PyMuPDF (fitz), PyPDF2
- **Frontend**: Vanilla HTML/CSS/JS, CSS Variables dark theme
- **Auth**: SHA-256 hashing, Gmail SMTP verification

---

## 📁 Project Structure

```
JK-SecuOne/
├── app.py                          # FastAPI main server (routes, API, DB, auth)
├── pentera_ISMS_P.py               # Pentera PDF extraction + ISMS-P mapping
├── sentinelOne_ISMS_P.py           # SentinelOne analysis pipeline (PDF/CSV)
├── requirements.txt                # Python dependencies
├── ISMS_P.csv                      # ISMS-P certification criteria data
├── pentera_Vulnerabilities.csv     # Vulnerability-to-number mapping (41 entries)
│
├── static/
│   ├── css/style.css               # Global styles (CSS variables, dark theme)
│   ├── images/                     # Logos (JK SecuOne, Pentera, SentinelOne)
│   └── js/
│       ├── main.js                 # Dashboard (upload, analysis, results)
│       ├── mypage.js               # Profile, admin, scan history, pricing
│       └── signup.js               # Signup form validation
│
└── templates/
    ├── dashboard.html              # Main dashboard
    ├── login.html                  # Login page
    ├── signup.html                 # Registration page
    ├── forgot_password.html        # Password recovery (3-step)
    └── mypage.html                 # Profile / admin / pricing / history
```

---

## 🚀 Quick Start

### 📋 System Requirements

| Item | Minimum | Recommended |
|------|---------|-------------|
| Python | 3.8+ | 3.10+ |
| RAM | 4GB | 8GB+ |
| Tesseract OCR | — | Optional (EasyOCR is primary) |
| GPU | — | CUDA-capable (for EasyOCR acceleration) |

### 🛠️ Installation

```bash
# 1. Clone repository
git clone https://github.com/xmin-02/JK-SecuOne.git
cd JK-SecuOne

# 2. Install dependencies
pip install -r requirements.txt
```

### ▶️ Run

```bash
python app.py
# Server: http://localhost:5050
# API Docs: http://localhost:5050/docs
```

---

## 🔄 How It Works

```
           ┌─────────────┐
           │   Browser    │
           │  (Vanilla JS)│
           └──────┬───────┘
                  │ REST API
                  ▼
           ┌─────────────┐
           │   FastAPI    │
           │  (app.py)    │
           └──┬───────┬───┘
              │       │
     ┌────────▼──┐ ┌──▼────────┐
     │  Pentera   │ │ SentinelOne│
     │  Pipeline  │ │  Pipeline  │
     └────────┬───┘ └──┬────────┘
              │        │
         PDF→OCR   PDF→OCR / CSV
              │        │
              ▼        ▼
         ┌─────────────────┐
         │  ISMS-P Mapping  │
         │  (CSV / Built-in)│
         └────────┬────────┘
                  │
                  ▼
         ┌─────────────────┐
         │    SQLite DB     │
         │ (users, history) │
         └─────────────────┘
```

### Pentera Pipeline
1. Upload PDF → Find Table of Contents → Locate "Achievements" page
2. Extract entries across pages: `#number`, `severity`, `name`
3. Map vulnerability name → `pentera_Vulnerabilities.csv` → `#number`
4. Map `#number` → `ISMS_P.csv` → certification controls (category, criteria, details)

### SentinelOne Pipeline
1. Upload PDF or CSV
2. PDF: OCR with EasyOCR → parse threat count, mitigation status, classifications, devices
3. CSV: Direct field parsing
4. Map classifications (Malware, Ransomware, Trojan, etc.) → built-in ISMS-P control table

---

## 🌐 API Endpoints

### Analysis
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/analyze/pentera` | Analyze Pentera PDF report |
| `POST` | `/api/analyze/sentinelone` | Analyze SentinelOne PDF/CSV report |
| `GET` | `/api/health` | Health check |

### Authentication
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/auth/signup` | User registration |
| `POST` | `/api/auth/login` | Login |
| `POST` | `/api/auth/send-verification` | Send email verification code |
| `POST` | `/api/auth/verify-code` | Verify email code |
| `POST` | `/api/auth/verify-email` | Verify identity for password recovery |
| `POST` | `/api/auth/reset-password` | Reset password |

### User & Scan History
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/user/profile/{id}` | Get user profile |
| `PUT` | `/api/user/update-basic` | Update name / username / phone |
| `PUT` | `/api/user/update-email` | Change email (with re-verification) |
| `PUT` | `/api/user/change-plan` | Change subscription plan |
| `POST` | `/api/scan/save` | Save scan result |
| `GET` | `/api/scan/history/{user_id}` | Get scan history (deduplicated) |
| `GET` | `/api/scan/detail/{scan_id}` | Get scan details |
| `DELETE` | `/api/scan/delete/{scan_id}` | Soft-delete scan |

### Admin
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/admin/stats` | Dashboard statistics |
| `GET` | `/api/admin/users` | List all users |
| `PUT` | `/api/admin/user/{id}/plan` | Change user plan |
| `DELETE` | `/api/admin/user/{id}` | Delete user |

---

## 💰 Plan Tiers

| Plan | SentinelOne Scans | Pentera Scans | Price |
|------|-------------------|---------------|-------|
| Free | 10 | 1 | Free |
| Sentinel One + | Unlimited | 2 | — |
| Pentera + | 20 | Unlimited | — |
| Premium + | Unlimited | Unlimited | — |

---

## 📄 License

This project is distributed under the MIT License.

---
---

# 🛡️ JK SecuOne - 보안 취약점 ISMS-P 매핑 대시보드

**JK SecuOne**은 Pentera/SentinelOne 보고서에서 다중 OCR 엔진으로 취약점을 자동 추출하고, ISMS-P 인증기준에 매핑하는 웹 기반 보안 컴플라이언스 플랫폼입니다.
FastAPI 백엔드와 순수 JavaScript 프론트엔드로 구성되어 있습니다.

---

## ✨ 주요 기능

### 🎯 핵심 기능
- **Pentera 보고서 분석** — PDF에서 OCR로 취약점 추출, 2단계 CSV 매핑으로 ISMS-P 연결
- **SentinelOne 보고서 분석** — PDF/CSV 위협 파싱, 분류별 ISMS-P 통제 항목 매핑
- **다중 OCR 엔진** — EasyOCR(한국어+영어) 주력, Tesseract 폴백, PyMuPDF 텍스트 레이어 추출
- **ISMS-P 준수 대시보드** — 통제 항목별 조치율, 위반 상태, 조치 안내
- **검사 이력 관리** — 자동 저장, 중복 제거, 소프트 삭제, 상세 결과 재조회

### 👤 사용자 관리
- **이메일 인증 회원가입** — Gmail SMTP 6자리 인증코드 (10분 유효)
- **플랜 기반 사용 한도** — Free / Sentinel One+ / Pentera+ / Premium 4단계
- **관리자 패널** — 사용자 관리, 플랜 변경, 검사 통계, 이력 초기화
- **비밀번호 찾기** — 3단계 (본인 확인 → 이메일 인증 → 재설정)

### 🤖 기술 스택
- **백엔드**: FastAPI + Uvicorn, SQLite3
- **OCR 엔진**: EasyOCR, Tesseract (pytesseract), PyMuPDF (fitz), PyPDF2
- **프론트엔드**: 순수 HTML/CSS/JS, CSS Variables 다크 테마
- **인증**: SHA-256 해싱, Gmail SMTP 인증

---

## 📁 프로젝트 구조

```
JK-SecuOne/
├── app.py                          # FastAPI 메인 서버 (라우트, API, DB, 인증)
├── pentera_ISMS_P.py               # Pentera PDF 추출 + ISMS-P 매핑
├── sentinelOne_ISMS_P.py           # SentinelOne 분석 파이프라인 (PDF/CSV)
├── requirements.txt                # Python 의존성
├── ISMS_P.csv                      # ISMS-P 인증기준 데이터
├── pentera_Vulnerabilities.csv     # 취약점-번호 매핑 (41개)
│
├── static/
│   ├── css/style.css               # 전역 스타일 (CSS 변수, 다크 테마)
│   ├── images/                     # 로고 (JK SecuOne, Pentera, SentinelOne)
│   └── js/
│       ├── main.js                 # 대시보드 (업로드, 분석, 결과 표시)
│       ├── mypage.js               # 프로필, 관리자, 검사 이력, 요금제
│       └── signup.js               # 회원가입 폼 검증
│
└── templates/
    ├── dashboard.html              # 메인 대시보드
    ├── login.html                  # 로그인
    ├── signup.html                 # 회원가입
    ├── forgot_password.html        # 비밀번호 찾기 (3단계)
    └── mypage.html                 # 마이페이지 / 관리자 / 요금제 / 이력
```

---

## 🚀 빠른 시작

### 📋 시스템 요구사항

| 항목 | 최소 | 권장 |
|------|------|------|
| Python | 3.8+ | 3.10+ |
| RAM | 4GB | 8GB+ |
| Tesseract OCR | — | 선택 (EasyOCR이 주력) |
| GPU | — | CUDA 지원 (EasyOCR 가속) |

### 🛠️ 설치

```bash
# 1. 저장소 클론
git clone https://github.com/xmin-02/JK-SecuOne.git
cd JK-SecuOne

# 2. 의존성 설치
pip install -r requirements.txt
```

### ▶️ 실행

```bash
python app.py
# 서버 주소: http://localhost:5050
# API 문서: http://localhost:5050/docs
```

---

## 🔄 동작 방식

### Pentera 파이프라인
1. PDF 업로드 → 목차(Table of Contents) 탐색 → Achievements 페이지 위치 파악
2. 다중 페이지에 걸쳐 항목 추출: `#번호`, `심각도`, `취약점명`
3. 취약점명 → `pentera_Vulnerabilities.csv` → `#번호` 매핑
4. `#번호` → `ISMS_P.csv` → 인증기준 (분류, 항목, 주요 확인사항, 관련 법규, 미흡사례)

### SentinelOne 파이프라인
1. PDF 또는 CSV 업로드
2. PDF: EasyOCR로 OCR → 위협 수, 조치 상태, 분류(Malware/Ransomware/Trojan 등), 기기 정보 파싱
3. CSV: 필드 직접 파싱
4. 위협 분류별 내장 ISMS-P 통제 항목 매핑:

| 분류 | ISMS-P 매핑 |
|------|------------|
| Malware | 2.8.4 악성코드 통제, 2.7.1 침해사고 예방, 2.7.2 대응/복구 |
| Ransomware | 위 항목 + 2.11.1 백업/복구, 2.9.1 암호정책 |
| Trojan | 2.8.4, 2.8.5 침입 탐지/차단, 2.3.3 접근 관리, 2.7.2 |
| Suspicious | 2.8.5, 2.7.1, 2.3.3 |
| PUP | 2.3.3, 2.8.4 |

---

## 🌐 API 엔드포인트

### 분석
| 메서드 | 경로 | 설명 |
|--------|------|------|
| `POST` | `/api/analyze/pentera` | Pentera PDF 보고서 분석 |
| `POST` | `/api/analyze/sentinelone` | SentinelOne PDF/CSV 보고서 분석 |
| `GET` | `/api/health` | 서버 상태 확인 |

### 인증
| 메서드 | 경로 | 설명 |
|--------|------|------|
| `POST` | `/api/auth/signup` | 회원가입 |
| `POST` | `/api/auth/login` | 로그인 |
| `POST` | `/api/auth/send-verification` | 이메일 인증번호 발송 |
| `POST` | `/api/auth/verify-code` | 인증번호 확인 |
| `POST` | `/api/auth/verify-email` | 비밀번호 찾기 본인 확인 |
| `POST` | `/api/auth/reset-password` | 비밀번호 재설정 |

### 사용자 & 검사 이력
| 메서드 | 경로 | 설명 |
|--------|------|------|
| `GET` | `/api/user/profile/{id}` | 프로필 조회 |
| `PUT` | `/api/user/update-basic` | 이름 / 아이디 / 연락처 수정 |
| `PUT` | `/api/user/update-email` | 이메일 변경 (재인증 필요) |
| `PUT` | `/api/user/change-plan` | 요금제 변경 |
| `POST` | `/api/scan/save` | 검사 결과 저장 |
| `GET` | `/api/scan/history/{user_id}` | 검사 이력 조회 (중복 제거) |
| `GET` | `/api/scan/detail/{scan_id}` | 검사 상세 조회 |
| `DELETE` | `/api/scan/delete/{scan_id}` | 검사 이력 삭제 |

### 관리자
| 메서드 | 경로 | 설명 |
|--------|------|------|
| `GET` | `/api/admin/stats` | 대시보드 통계 |
| `GET` | `/api/admin/users` | 전체 사용자 목록 |
| `PUT` | `/api/admin/user/{id}/plan` | 사용자 플랜 변경 |
| `DELETE` | `/api/admin/user/{id}` | 사용자 삭제 |

---

## 💰 요금제

| 플랜 | SentinelOne 검사 | Pentera 검사 | 가격 |
|------|------------------|--------------|------|
| Free | 10회 | 1회 | 무료 |
| Sentinel One + | 무제한 | 2회 | — |
| Pentera + | 20회 | 무제한 | — |
| Premium + | 무제한 | 무제한 | — |

---

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

---
