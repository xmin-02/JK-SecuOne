"""
보안 취약점 분석 대시보드 - FastAPI 백엔드
Pentera 및 SentinelOne 보고서를 분석하여 ISMS-P 매핑 제공
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from pathlib import Path
import tempfile
import shutil
from typing import List, Dict, Optional
import uvicorn
import sqlite3
import hashlib
import secrets
import re
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# pentera_ISMS_P 모듈 임포트
from pentera_ISMS_P import PenteraPDFExtractor, ISMSPMapper

app = FastAPI(
    title="보안 취약점 분석 대시보드",
    description="Pentera/SentinelOne 보고서를 ISMS-P 기준과 매핑",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 정적 파일 및 템플릿 디렉토리 설정
static_dir = Path(__file__).parent / "static"
templates_dir = Path(__file__).parent / "templates"

# 디렉토리 생성
static_dir.mkdir(exist_ok=True)
templates_dir.mkdir(exist_ok=True)
(static_dir / "css").mkdir(exist_ok=True)
(static_dir / "js").mkdir(exist_ok=True)

# 정적 파일 서빙
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", response_class=HTMLResponse)
async def read_root():
    """메인 대시보드 페이지"""
    html_file = templates_dir / "dashboard.html"
    if html_file.exists():
        return html_file.read_text(encoding='utf-8')
    return """
    <html>
        <head><title>보안 취약점 분석 대시보드</title></head>
        <body>
            <h1>대시보드를 로드하는 중...</h1>
            <p>templates/dashboard.html 파일을 생성 중입니다.</p>
        </body>
    </html>
    """


@app.get("/login", response_class=HTMLResponse)
async def login_page():
    """로그인 페이지"""
    html_file = templates_dir / "login.html"
    if html_file.exists():
        return html_file.read_text(encoding='utf-8')
    return HTMLResponse(content="<h1>로그인 페이지를 찾을 수 없습니다.</h1>", status_code=404)


@app.get("/signup", response_class=HTMLResponse)
async def signup_page():
    """회원가입 페이지"""
    html_file = templates_dir / "signup.html"
    if html_file.exists():
        return html_file.read_text(encoding='utf-8')
    return HTMLResponse(content="<h1>회원가입 페이지를 찾을 수 없습니다.</h1>", status_code=404)


@app.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page():
    """비밀번호 찾기 페이지"""
    html_file = templates_dir / "forgot_password.html"
    if html_file.exists():
        return html_file.read_text(encoding='utf-8')
    return HTMLResponse(content="<h1>비밀번호 찾기 페이지를 찾을 수 없습니다.</h1>", status_code=404)


@app.get("/mypage", response_class=HTMLResponse)
async def mypage():
    """마이페이지"""
    html_file = templates_dir / "mypage.html"
    if html_file.exists():
        return html_file.read_text(encoding='utf-8')
    return HTMLResponse(content="<h1>마이페이지를 찾을 수 없습니다.</h1>", status_code=404)


@app.post("/api/analyze/pentera")
async def analyze_pentera_report(
    file: UploadFile = File(...),
    vulnerabilities_csv: UploadFile = File(None),
    isms_csv: UploadFile = File(None)
):
    """
    Pentera 보고서 분석 API
    
    Args:
        file: Pentera PDF 보고서
        vulnerabilities_csv: 취약점 매핑 CSV (선택)
        isms_csv: ISMS-P 매핑 CSV (선택)
        
    Returns:
        분석 결과 JSON
    """
    # PDF 파일 검증
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="PDF 파일만 업로드 가능합니다.")
    
    try:
        # 임시 파일로 저장
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_pdf:
            shutil.copyfileobj(file.file, tmp_pdf)
            pdf_path = tmp_pdf.name
        
        # CSV 파일 처리
        vuln_csv_path = "pentera_Vulnerabilities.csv"
        isms_csv_path = "ISMS_P.csv"
        
        if vulnerabilities_csv:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as tmp_csv:
                shutil.copyfileobj(vulnerabilities_csv.file, tmp_csv)
                vuln_csv_path = tmp_csv.name
        
        if isms_csv:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as tmp_csv:
                shutil.copyfileobj(isms_csv.file, tmp_csv)
                isms_csv_path = tmp_csv.name
        
        # PDF 분석
        extractor = PenteraPDFExtractor(pdf_path)
        vulnerabilities = extractor.process()
        
        if not vulnerabilities:
            return JSONResponse(
                status_code=200,
                content={
                    "status": "warning",
                    "message": "취약점을 찾을 수 없습니다.",
                    "vulnerabilities": [],
                    "total": 0,
                    "mapped": 0,
                    "unmapped": 0
                }
            )
        
        # ISMS-P 매핑
        mapper = ISMSPMapper(vuln_csv_path, isms_csv_path)
        
        results = []
        mapped_count = 0
        
        for vuln in vulnerabilities:
            isms_result = mapper.get_isms_violations(vuln['name'])
            
            if isms_result:
                mapped_count += 1
                results.append({
                    "vulnerability": vuln['name'],
                    "severity": vuln['severity'],
                    "number": vuln['number'],
                    "isms_violations": [
                        {
                            "category": v.get('분류', ''),
                            "item": v.get('항목', ''),
                            "criteria": v.get('인증기준', ''),
                            "details": v.get('세부 설명', v.get('인증기준', ''))
                        }
                        for v in isms_result.get('violations', [])
                    ],
                    "mapped": True
                })
            else:
                results.append({
                    "vulnerability": vuln['name'],
                    "severity": vuln['severity'],
                    "number": vuln['number'],
                    "isms_violations": [],
                    "mapped": False
                })
        
        # 임시 파일 정리
        Path(pdf_path).unlink(missing_ok=True)
        if vulnerabilities_csv and Path(vuln_csv_path) != Path("pentera_Vulnerabilities.csv"):
            Path(vuln_csv_path).unlink(missing_ok=True)
        if isms_csv and Path(isms_csv_path) != Path("ISMS_P.csv"):
            Path(isms_csv_path).unlink(missing_ok=True)
        
        # 검사 결과를 JSON으로 저장 (DB 저장용)
        response_data = {
            "status": "success",
            "message": f"분석 완료: {len(vulnerabilities)}개 취약점 발견",
            "vulnerabilities": results,
            "total": len(vulnerabilities),
            "mapped": mapped_count,
            "unmapped": len(vulnerabilities) - mapped_count,
            "filename": file.filename
        }
        
        return response_data
        
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"분석 오류 발생:\n{error_detail}")
        raise HTTPException(status_code=500, detail=f"분석 중 오류 발생: {str(e)}")


@app.post("/api/analyze/sentinelone")
async def analyze_sentinelone_report(file: UploadFile = File(...)):
    """
    SentinelOne 보고서 분석 API (PDF 또는 CSV)
    
    Args:
        file: SentinelOne PDF 또는 CSV 보고서
        
    Returns:
        분석 결과 JSON
    """
    # 파일 타입 검증
    if not (file.filename.endswith('.pdf') or file.filename.endswith('.csv')):
        raise HTTPException(status_code=400, detail="PDF 또는 CSV 파일만 업로드 가능합니다.")
    
    try:
        # 임시 파일로 저장
        file_extension = '.csv' if file.filename.endswith('.csv') else '.pdf'
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp_file:
            shutil.copyfileobj(file.file, tmp_file)
            file_path = tmp_file.name
        
        from sentinelOne_ISMS_P import (
            pdf_to_ocr_json,
            extract_all_text,
            parse_threat_count,
            parse_mitigated_count,
            parse_classifications,
            parse_devices,
            generate_threat_items,
            parse_threats_csv,
            analyze_threat,
            calculate_stats,
            detect_report_target,
            CONTROL_DESCRIPTIONS
        )
        
        # CSV 파일 처리
        if file.filename.endswith('.csv'):
            print(f"[INFO] CSV 파일 처리 중...", file=sys.stderr)
            threats_data = parse_threats_csv(Path(file_path))
            
            if not threats_data:
                Path(file_path).unlink(missing_ok=True)
                return {
                    "status": "success",
                    "message": "위협이 탐지되지 않았습니다.",
                    "threats": [],
                    "total": 0,
                    "mitigated": 0,
                    "active": 0,
                    "mitigation_rate": 0,
                    "filename": file.filename,
                    "report_type": "그룹",
                    "report_target": "CSV Import"
                }
            
            # CSV 데이터를 표준 형식으로 변환
            analyses = [analyze_threat(threat) for threat in threats_data]
            stats = calculate_stats(analyses)
            
            # 보고서 대상 (CSV는 기본값)
            report_type = "그룹"
            report_target = "CSV Import"
            devices = list(set([t.get('device_name', 'Unknown') for t in threats_data]))[:10]
            
        else:
            # PDF 파일 처리
            ocr_json = pdf_to_ocr_json(Path(file_path))
            text = extract_all_text(ocr_json)
            
            # 위협 정보 파싱
            threat_count = parse_threat_count(text)
            mitigated, not_mitigated = parse_mitigated_count(text)
            classifications = parse_classifications(text)
            devices = parse_devices(text)
            
            if not classifications:
                classifications = {"general": threat_count}
            
            if threat_count == 0:
                Path(file_path).unlink(missing_ok=True)
                return {
                    "status": "success",
                    "message": "위협이 탐지되지 않았습니다.",
                    "threats": [],
                    "total": 0,
                    "mitigated": 0,
                    "active": 0,
                    "mitigation_rate": 0,
                    "filename": file.filename,
                    "report_type": "그룹",
                    "report_target": "알 수 없음"
                }
            
            # 위협 항목 생성 및 분석
            threat_items = generate_threat_items(threat_count, mitigated, classifications, devices)
            analyses = [analyze_threat(t) for t in threat_items]
            stats = calculate_stats(analyses)
            
            # 보고서 대상 추출
            report_type, report_target, _ = detect_report_target(text, file.filename)
        
        # ISMS-P 제어 항목별 통계 (PDF/CSV 공통)
        control_map = {}
        for analysis in analyses:
            for control in analysis.isms_controls:
                if control not in control_map:
                    control_map[control] = {
                        "total": 0,
                        "mitigated": 0,
                        "active": 0,
                        "classifications": []
                    }
                control_map[control]["total"] += 1
                control_map[control]["classifications"].append(analysis.classification.lower())
                if analysis.status == "Mitigated":
                    control_map[control]["mitigated"] += 1
                else:
                    control_map[control]["active"] += 1
        
        # 결과 포맷팅
        threats = []
        for analysis in analyses:
            threat_data = {
                "threat_name": analysis.threat_name,
                "classification": analysis.classification,
                "device_name": analysis.device_name,
                "status": analysis.status,
                "violation_status": analysis.violation_status,
                "confidence": analysis.confidence,
                "isms_controls": [
                    {
                        "code": control,
                        "title": CONTROL_DESCRIPTIONS.get(control, {}).get("title", control),
                        "action": CONTROL_DESCRIPTIONS.get(control, {}).get("action", "조치")
                    }
                    for control in analysis.isms_controls
                ],
                "mapped": len(analysis.isms_controls) > 0
            }
            
            if analysis.file_hash:
                threat_data["file_hash"] = analysis.file_hash
            
            threats.append(threat_data)
        
        # 제어 항목 요약
        controls_summary = []
        for control, counts in sorted(control_map.items()):
            mitigation_rate = (counts["mitigated"] / counts["total"] * 100) if counts["total"] > 0 else 0
            control_info = CONTROL_DESCRIPTIONS.get(control, {"title": control, "action": "조치"})
            
            # 위협 유형별 통계
            class_summary = {}
            for c in counts["classifications"]:
                class_summary[c] = class_summary.get(c, 0) + 1
            
            controls_summary.append({
                "code": control,
                "title": control_info["title"],
                "action": control_info["action"],
                "total": counts["total"],
                "mitigated": counts["mitigated"],
                "active": counts["active"],
                "mitigation_rate": round(mitigation_rate, 1),
                "status": "적합" if mitigation_rate >= 80 else "부분 적합" if mitigation_rate >= 50 else "부적합",
                "threat_types": class_summary
            })
        
        # 임시 파일 정리
        Path(file_path).unlink(missing_ok=True)
        
        response_data = {
            "status": "success",
            "message": f"분석 완료: {threat_count}개 위협 탐지",
            "threats": threats,
            "total": stats["total"],
            "mitigated": stats["mitigated"],
            "active": stats["active"],
            "mitigation_rate": round(stats["mitigation_rate"], 1),
            "controls": controls_summary,
            "filename": file.filename,
            "report_type": report_type,
            "report_target": report_target,
            "devices": devices[:10] if devices else []  # 최대 10개 기기만 표시
        }
        
        return response_data
        
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"SentinelOne 분석 오류:\n{error_detail}")
        
        # 임시 파일 정리
        try:
            if 'pdf_path' in locals():
                Path(pdf_path).unlink(missing_ok=True)
        except:
            pass
        
        raise HTTPException(status_code=500, detail=f"분석 중 오류 발생: {str(e)}")


@app.get("/api/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    return {
        "status": "healthy",
        "service": "Security Vulnerability Analysis Dashboard",
        "version": "1.0.0"
    }


# ============================================================================
# 데이터베이스 및 인증 관련 설정
# ============================================================================

# 데이터베이스 파일 경로
DB_FILE = Path(__file__).parent / "users.db"

# 이메일 인증 코드 저장소 (메모리)
verification_codes = {}

# Gmail SMTP 설정
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_EMAIL = "smartit.ngms@gmail.com"
SMTP_PASSWORD = "gxut kmss jrjo obaq"


# Pydantic 모델
class EmailVerification(BaseModel):
    email: EmailStr


class CodeVerification(BaseModel):
    email: EmailStr
    code: str


class UsernameCheck(BaseModel):
    username: str


class SignupData(BaseModel):
    name: str
    phone: str
    email: EmailStr
    username: str
    password: str


class LoginData(BaseModel):
    username: str
    password: str


# 데이터베이스 초기화
def init_db():
    """사용자 데이터베이스 초기화"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            plan TEXT DEFAULT 'free',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scan_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            scan_type TEXT DEFAULT 'pentera',
            total_vulnerabilities INTEGER NOT NULL,
            mapped_count INTEGER NOT NULL,
            unmapped_count INTEGER NOT NULL,
            scan_results TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    
    # scan_type 컬럼이 없는 기존 테이블에 추가
    try:
        cursor.execute("ALTER TABLE scan_history ADD COLUMN scan_type TEXT DEFAULT 'pentera'")
    except sqlite3.OperationalError:
        pass  # 컬럼이 이미 존재하면 무시
    
    # plan 컬럼이 없는 기존 users 테이블에 추가
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN plan TEXT DEFAULT 'free'")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # 컬럼이 이미 존재하면 무시
    
    # 기존 사용자들의 plan을 'free'로 업데이트
    cursor.execute("UPDATE users SET plan = 'free' WHERE plan IS NULL OR plan = ''")
    
    conn.commit()
    conn.close()


# 앱 시작 시 DB 초기화
init_db()


# 비밀번호 해싱
def hash_password(password: str) -> str:
    """비밀번호를 SHA-256으로 해싱"""
    return hashlib.sha256(password.encode()).hexdigest()


# 인증번호 생성
def generate_verification_code() -> str:
    """6자리 숫자 인증번호 생성"""
    return ''.join([str(secrets.randbelow(10)) for _ in range(6)])


# 인증번호 저장소
verification_codes = {}


def send_verification_email(to_email: str, code: str) -> bool:
    """인증번호 이메일 발송"""
    subject = "보안 취약점 분석 대시보드 - 이메일 인증"
    body = f"""
        <h2 style="color: #6366f1; margin-bottom: 20px;">이메일 인증번호</h2>
        <p style="font-size: 16px; margin-bottom: 20px;">아래 인증번호를 입력하여 인증을 완료해주세요.</p>
        <div style="background: #f3f4f6; padding: 20px; text-align: center; border-radius: 8px; margin: 20px 0;">
            <p style="font-size: 14px; color: #6b7280; margin: 0 0 10px 0;">인증번호</p>
            <p style="font-size: 32px; font-weight: bold; color: #6366f1; letter-spacing: 8px; margin: 0;">{code}</p>
        </div>
        <p style="font-size: 14px; color: #6b7280;">인증번호는 10분간 유효합니다.</p>
    """
    return send_email(to_email, subject, body)


# 이메일 발송
def send_email(to_email: str, subject: str, body: str) -> bool:
    """Gmail을 통한 이메일 발송"""
    try:
        # 이메일 메시지 생성
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = SMTP_EMAIL
        msg['To'] = to_email
        
        # HTML 본문
        html_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f9fafb;">
                    <div style="background: linear-gradient(135deg, #6366f1, #8b5cf6); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                        <h1 style="color: white; margin: 0; font-size: 24px;">🛡️ 보안 취약점 분석 대시보드</h1>
                    </div>
                    <div style="background: white; padding: 30px; border-radius: 0 0 10px 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                        {body}
                    </div>
                    <div style="text-align: center; margin-top: 20px; color: #6b7280; font-size: 12px;">
                        <p>본 메일은 발신 전용입니다. 문의사항은 관리자에게 연락해주세요.</p>
                        <p>&copy; 2025 보안 취약점 분석 대시보드. All rights reserved.</p>
                    </div>
                </div>
            </body>
        </html>
        """
        
        msg.attach(MIMEText(html_body, 'html'))
        
        # SMTP 서버 연결 및 발송
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_EMAIL, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        return True
    except Exception as e:
        print(f"이메일 발송 오류: {e}")
        return False


# ============================================================================
# 인증 API 엔드포인트
# ============================================================================

@app.post("/api/auth/send-verification")
async def send_verification_code(data: EmailVerification):
    """이메일 인증번호 발송"""
    try:
        # 인증번호 생성
        code = generate_verification_code()
        
        # 메모리에 저장 (10분 유효)
        verification_codes[data.email] = {
            'code': code,
            'expires_at': datetime.now() + timedelta(minutes=10)
        }
        
        # 이메일 본문
        email_body = f"""
        <h2 style="color: #6366f1;">이메일 인증</h2>
        <p>회원가입을 위한 인증번호입니다.</p>
        <div style="background: #f3f4f6; padding: 20px; border-radius: 8px; text-align: center; margin: 20px 0;">
            <h1 style="color: #6366f1; font-size: 36px; letter-spacing: 8px; margin: 0;">{code}</h1>
        </div>
        <p>위 인증번호를 입력하여 이메일 인증을 완료해주세요.</p>
        <p style="color: #ef4444; font-weight: bold;">인증번호는 10분간 유효합니다.</p>
        <p style="color: #6b7280; font-size: 14px; margin-top: 30px;">
            본인이 요청하지 않은 경우, 이 메일을 무시하셔도 됩니다.
        </p>
        """
        
        # 이메일 발송
        if send_email(data.email, "보안 취약점 분석 대시보드 - 이메일 인증", email_body):
            return {"message": "인증번호가 발송되었습니다."}
        else:
            raise HTTPException(status_code=500, detail="이메일 발송에 실패했습니다.")
    
    except Exception as e:
        print(f"인증번호 발송 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/auth/verify-code")
async def verify_email_code(data: CodeVerification):
    """이메일 인증번호 확인"""
    # 인증번호 확인
    if data.email not in verification_codes:
        raise HTTPException(status_code=400, detail="인증번호가 발송되지 않았습니다.")
    
    stored_data = verification_codes[data.email]
    
    # 유효기간 확인
    if datetime.now() > stored_data['expires_at']:
        del verification_codes[data.email]
        raise HTTPException(status_code=400, detail="인증번호가 만료되었습니다.")
    
    # 인증번호 일치 확인
    if data.code != stored_data['code']:
        raise HTTPException(status_code=400, detail="인증번호가 일치하지 않습니다.")
    
    # 인증 성공 - 인증번호 삭제
    del verification_codes[data.email]
    
    return {"message": "이메일 인증이 완료되었습니다."}


@app.post("/api/auth/check-username")
async def check_username_availability(data: UsernameCheck):
    """아이디 중복 확인"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE username = ?", (data.username,))
    count = cursor.fetchone()[0]
    
    conn.close()
    
    return {"available": count == 0}


@app.post("/api/auth/signup")
async def signup_user(data: SignupData):
    """회원가입 처리"""
    try:
        # 연락처 포맷 검증 및 변환
        phone = re.sub(r'[^0-9]', '', data.phone)
        if len(phone) == 11:
            formatted_phone = f"{phone[:3]}-{phone[3:7]}-{phone[7:]}"
        else:
            raise HTTPException(status_code=400, detail="올바른 연락처 형식이 아닙니다.")
        
        # 비밀번호 해싱
        password_hash = hash_password(data.password)
        
        # DB에 저장
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO users (name, phone, email, username, password_hash, plan)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (data.name, formatted_phone, data.email, data.username, password_hash, 'free'))
            
            conn.commit()
            user_id = cursor.lastrowid
            
            conn.close()
            
            return {
                "message": "회원가입이 완료되었습니다.",
                "user_id": user_id
            }
        
        except sqlite3.IntegrityError:
            conn.close()
            raise HTTPException(status_code=400, detail="이미 사용 중인 이메일 또는 아이디입니다.")
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"회원가입 오류: {e}")
        raise HTTPException(status_code=500, detail="회원가입 처리 중 오류가 발생했습니다.")


@app.post("/api/auth/login")
async def login_user(data: LoginData):
    """로그인 처리"""
    try:
        # DB에서 사용자 조회
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, name, username, password_hash
            FROM users
            WHERE username = ?
        """, (data.username,))
        
        user = cursor.fetchone()
        conn.close()
        
        # 사용자가 없으면
        if not user:
            raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 일치하지 않습니다.")
        
        user_id, name, username, stored_password_hash = user
        
        # 비밀번호 확인
        input_password_hash = hash_password(data.password)
        
        if input_password_hash != stored_password_hash:
            raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 일치하지 않습니다.")
        
        # 로그인 성공
        return {
            "message": "로그인 성공",
            "user": {
                "id": user_id,
                "name": name,
                "username": username
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"로그인 오류: {e}")
        raise HTTPException(status_code=500, detail="로그인 처리 중 오류가 발생했습니다.")


@app.get("/api/user/profile/{user_id}")
async def get_user_profile(user_id: int):
    """사용자 프로필 조회"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, name, phone, email, username, plan, created_at, scan_count
            FROM users
            WHERE id = ?
        """, (user_id,))
        
        user = cursor.fetchone()
        conn.close()
        
        if not user:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
        
        return {
            "id": user[0],
            "name": user[1],
            "phone": user[2],
            "email": user[3],
            "username": user[4],
            "plan": user[5],
            "created_at": user[6],
            "scan_count": user[7] if user[7] is not None else 0
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"프로필 조회 오류: {e}")
        raise HTTPException(status_code=500, detail="프로필 조회 중 오류가 발생했습니다.")


@app.post("/api/scan/save")
async def save_scan_history(data: dict):
    """검사 이력 저장"""
    try:
        import json
        
        user_id = data.get('user_id')
        filename = data.get('filename')
        scan_type = data.get('scan_type', 'pentera')  # 기본값 pentera
        total = data.get('total', 0)
        mapped = data.get('mapped', 0)
        unmapped = data.get('unmapped', 0)
        results = data.get('vulnerabilities', [])
        
        if not user_id or not filename:
            raise HTTPException(status_code=400, detail="필수 정보가 누락되었습니다.")
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO scan_history (user_id, filename, scan_type, total_vulnerabilities, mapped_count, unmapped_count, scan_results)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, filename, scan_type, total, mapped, unmapped, json.dumps(results, ensure_ascii=False)))
        
        # scan_count 증가
        cursor.execute("UPDATE users SET scan_count = scan_count + 1 WHERE id = ?", (user_id,))
        
        conn.commit()
        scan_id = cursor.lastrowid
        conn.close()
        
        return {"message": "검사 이력이 저장되었습니다.", "scan_id": scan_id}
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"검사 이력 저장 오류: {e}")
        raise HTTPException(status_code=500, detail="검사 이력 저장 중 오류가 발생했습니다.")


@app.get("/api/scan/history/{user_id}")
async def get_scan_history(user_id: int):
    """사용자 검사 이력 조회 - 삭제되지 않은 것만, 중복 파일명은 최신 것만"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # 파일명별로 가장 최신 검사만 선택 (deleted=0만)
        cursor.execute("""
            SELECT id, filename, scan_type, total_vulnerabilities, mapped_count, unmapped_count, created_at
            FROM (
                SELECT id, filename, scan_type, total_vulnerabilities, mapped_count, unmapped_count, created_at,
                       ROW_NUMBER() OVER (PARTITION BY filename ORDER BY created_at DESC) as rn
                FROM scan_history
                WHERE user_id = ? AND deleted = 0
            )
            WHERE rn = 1
            ORDER BY created_at DESC
        """, (user_id,))
        
        scans = cursor.fetchall()
        conn.close()
        
        return {
            "scans": [
                {
                    "id": scan[0],
                    "filename": scan[1],
                    "scan_type": scan[2] or 'pentera',
                    "total": scan[3],
                    "mapped": scan[4],
                    "unmapped": scan[5],
                    "date": scan[6]
                }
                for scan in scans
            ]
        }
    
    except Exception as e:
        print(f"검사 이력 조회 오류: {e}")
        raise HTTPException(status_code=500, detail="검사 이력 조회 중 오류가 발생했습니다.")


@app.get("/api/scan/usage-history/{user_id}")
async def get_usage_history(user_id: int):
    """사용자 사용 내역 조회 - 삭제된 것 포함, 모든 기록"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # 모든 검사 기록 조회 (deleted 무관)
        cursor.execute("""
            SELECT id, filename, scan_type, total_vulnerabilities, mapped_count, unmapped_count, created_at
            FROM scan_history
            WHERE user_id = ?
            ORDER BY created_at DESC
        """, (user_id,))
        
        scans = cursor.fetchall()
        conn.close()
        
        return {
            "scans": [
                {
                    "id": scan[0],
                    "filename": scan[1],
                    "scan_type": scan[2] or 'pentera',
                    "total": scan[3],
                    "mapped": scan[4],
                    "unmapped": scan[5],
                    "date": scan[6]
                }
                for scan in scans
            ]
        }
    
    except Exception as e:
        print(f"사용 내역 조회 오류: {e}")
        raise HTTPException(status_code=500, detail="사용 내역 조회 중 오류가 발생했습니다.")


@app.get("/api/scan/detail/{scan_id}")
async def get_scan_detail(scan_id: int):
    """검사 상세 정보 조회"""
    try:
        import json
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT filename, total_vulnerabilities, mapped_count, unmapped_count, scan_results, created_at
            FROM scan_history
            WHERE id = ?
        """, (scan_id,))
        
        scan = cursor.fetchone()
        conn.close()
        
        if not scan:
            raise HTTPException(status_code=404, detail="검사 이력을 찾을 수 없습니다.")
        
        return {
            "filename": scan[0],
            "total": scan[1],
            "mapped": scan[2],
            "unmapped": scan[3],
            "vulnerabilities": json.loads(scan[4]),
            "date": scan[5]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"검사 상세 조회 오류: {e}")
        raise HTTPException(status_code=500, detail="검사 상세 조회 중 오류가 발생했습니다.")


@app.delete("/api/scan/delete/{scan_id}")
async def delete_scan_history(scan_id: int):
    """검사 이력 삭제 - 동일 파일명의 모든 검사 삭제"""
    try:
        print(f"삭제 요청: scan_id={scan_id}")
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # 해당 검사의 user_id와 filename 조회
        cursor.execute("SELECT user_id, filename FROM scan_history WHERE id = ?", (scan_id,))
        scan_info = cursor.fetchone()
        print(f"검사 정보: {scan_info}")
        
        if not scan_info:
            conn.close()
            raise HTTPException(status_code=404, detail="검사 이력을 찾을 수 없습니다.")
        
        user_id, filename = scan_info
        
        # 같은 user_id와 filename을 가진 모든 검사를 deleted = 1로 표시
        cursor.execute("UPDATE scan_history SET deleted = 1 WHERE user_id = ? AND filename = ?", (user_id, filename))
        updated_count = cursor.rowcount
        print(f"삭제 표시된 행 수: {updated_count} (파일명: {filename})")
        
        conn.commit()
        conn.close()
        
        return {"message": "검사 이력이 삭제되었습니다.", "deleted_count": updated_count}
    except HTTPException:
        raise
    except Exception as e:
        print(f"검사 이력 삭제 오류: {e}")
        raise HTTPException(status_code=500, detail="검사 이력 삭제 중 오류가 발생했습니다.")

@app.delete("/api/user/delete-account")
async def delete_account(request: Request):
    """회원 탈퇴"""
    try:
        data = await request.json()
        user_id = data.get('user_id')
        password = data.get('password')
        
        if not user_id or not password:
            raise HTTPException(status_code=400, detail="필수 정보가 누락되었습니다.")
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # 사용자 정보 확인
        cursor.execute("SELECT password_hash FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        
        if not user:
            conn.close()
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
        
        # 비밀번호 확인
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        if password_hash != user[0]:
            conn.close()
            raise HTTPException(status_code=401, detail="비밀번호가 일치하지 않습니다.")
        
        # 검사 이력 삭제
        cursor.execute("DELETE FROM scan_history WHERE user_id = ?", (user_id,))
        
        # 사용자 삭제
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        
        conn.commit()
        conn.close()
        
        return {"message": "회원 탈퇴가 완료되었습니다."}
    except HTTPException:
        raise
    except Exception as e:
        print(f"회원 탈퇴 오류: {e}")
        raise HTTPException(status_code=500, detail="회원 탈퇴 중 오류가 발생했습니다.")

    
    except HTTPException:
        raise
    except Exception as e:
        print(f"검사 이력 삭제 오류: {e}")
        raise HTTPException(status_code=500, detail="검사 이력 삭제 중 오류가 발생했습니다.")


@app.post("/api/user/verify-password")
async def verify_password(data: dict):
    """비밀번호 확인"""
    try:
        user_id = data.get('user_id')
        password = data.get('password')
        
        if not user_id or not password:
            raise HTTPException(status_code=400, detail="필수 정보가 누락되었습니다.")
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute("SELECT password_hash FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        conn.close()
        
        if not user:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
        
        if hash_password(password) != user[0]:
            raise HTTPException(status_code=401, detail="비밀번호가 일치하지 않습니다.")
        
        return {"message": "비밀번호가 확인되었습니다."}
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"비밀번호 확인 오류: {e}")
        raise HTTPException(status_code=500, detail="비밀번호 확인 중 오류가 발생했습니다.")


@app.post("/api/user/check-username")
async def check_username(data: dict):
    """아이디 중복 검사"""
    try:
        username = data.get('username')
        user_id = data.get('user_id')  # 자기 자신 제외
        
        if not username:
            raise HTTPException(status_code=400, detail="아이디를 입력하세요.")
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        if user_id:
            cursor.execute("SELECT id FROM users WHERE username = ? AND id != ?", (username, user_id))
        else:
            cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        
        exists = cursor.fetchone()
        conn.close()
        
        return {"available": not exists}
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"아이디 중복 검사 오류: {e}")
        raise HTTPException(status_code=500, detail="아이디 중복 검사 중 오류가 발생했습니다.")


@app.put("/api/user/update-basic")
async def update_basic_info(data: dict):
    """기본 정보 업데이트 (이름, 아이디, 연락처)"""
    try:
        user_id = data.get('user_id')
        name = data.get('name')
        username = data.get('username')
        phone = data.get('phone')
        
        if not user_id:
            raise HTTPException(status_code=400, detail="사용자 ID가 필요합니다.")
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # 아이디 중복 확인 (자기 자신 제외)
        if username:
            cursor.execute("SELECT id FROM users WHERE username = ? AND id != ?", (username, user_id))
            if cursor.fetchone():
                conn.close()
                raise HTTPException(status_code=400, detail="이미 사용 중인 아이디입니다.")
        
        # 업데이트할 필드 구성
        updates = []
        params = []
        
        if name:
            updates.append("name = ?")
            params.append(name)
        if username:
            updates.append("username = ?")
            params.append(username)
        if phone:
            updates.append("phone = ?")
            params.append(phone)
        
        if not updates:
            conn.close()
            raise HTTPException(status_code=400, detail="수정할 정보가 없습니다.")
        
        params.append(user_id)
        cursor.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()
        
        # 업데이트된 정보 조회
        cursor.execute("SELECT id, name, username, email, phone FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        conn.close()
        
        return {
            "message": "정보가 수정되었습니다.",
            "user": {
                "id": user[0],
                "name": user[1],
                "username": user[2],
                "email": user[3],
                "phone": user[4]
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"기본 정보 수정 오류: {e}")
        raise HTTPException(status_code=500, detail="정보 수정 중 오류가 발생했습니다.")


@app.post("/api/user/update-email-verify")
async def send_email_verification_for_update(data: dict):
    """이메일 변경을 위한 인증번호 발송"""
    try:
        user_id = data.get('user_id')
        new_email = data.get('email')
        
        if not user_id or not new_email:
            raise HTTPException(status_code=400, detail="필수 정보가 누락되었습니다.")
        
        # 이메일 중복 확인
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE email = ? AND id != ?", (new_email, user_id))
        if cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=400, detail="이미 사용 중인 이메일입니다.")
        conn.close()
        
        # 인증번호 생성 및 저장
        code = generate_verification_code()
        verification_codes[new_email] = code
        
        # 이메일 발송
        send_verification_email(new_email, code)
        
        return {"message": "인증번호가 발송되었습니다."}
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"이메일 인증번호 발송 오류: {e}")
        raise HTTPException(status_code=500, detail="인증번호 발송 중 오류가 발생했습니다.")


@app.put("/api/user/update-email")
async def update_email(data: dict):
    """인증번호 확인 후 이메일 변경"""
    try:
        user_id = data.get('user_id')
        new_email = data.get('email')
        code = data.get('code')
        
        if not user_id or not new_email or not code:
            raise HTTPException(status_code=400, detail="필수 정보가 누락되었습니다.")
        
        # 인증번호 확인
        if new_email not in verification_codes or verification_codes[new_email] != code:
            raise HTTPException(status_code=400, detail="인증번호가 일치하지 않습니다.")
        
        # 이메일 업데이트
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET email = ? WHERE id = ?", (new_email, user_id))
        conn.commit()
        conn.close()
        
        # 인증번호 삭제
        del verification_codes[new_email]
        
        return {"message": "이메일이 변경되었습니다.", "email": new_email}
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"이메일 변경 오류: {e}")
        raise HTTPException(status_code=500, detail="이메일 변경 중 오류가 발생했습니다.")


@app.post("/api/user/update-password-verify")
async def send_verification_for_password_update(data: dict):
    """비밀번호 변경을 위한 인증번호 발송"""
    try:
        user_id = data.get('user_id')
        
        if not user_id:
            raise HTTPException(status_code=400, detail="사용자 ID가 필요합니다.")
        
        # 사용자 이메일 조회
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT email FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        conn.close()
        
        if not user:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
        
        email = user[0]
        
        # 인증번호 생성 및 저장
        code = generate_verification_code()
        verification_codes[f"password_{user_id}"] = code
        
        # 이메일 발송
        send_verification_email(email, code)
        
        return {"message": "인증번호가 발송되었습니다.", "email": email}
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"비밀번호 변경 인증번호 발송 오류: {e}")
        raise HTTPException(status_code=500, detail="인증번호 발송 중 오류가 발생했습니다.")


@app.put("/api/user/update-password")
async def update_password(data: dict):
    """인증번호 확인 후 비밀번호 변경"""
    try:
        user_id = data.get('user_id')
        new_password = data.get('password')
        code = data.get('code')
        
        if not user_id or not new_password or not code:
            raise HTTPException(status_code=400, detail="필수 정보가 누락되었습니다.")
        
        # 인증번호 확인
        key = f"password_{user_id}"
        if key not in verification_codes or verification_codes[key] != code:
            raise HTTPException(status_code=400, detail="인증번호가 일치하지 않습니다.")
        
        # 비밀번호 업데이트
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hash_password(new_password), user_id))
        conn.commit()
        conn.close()
        
        # 인증번호 삭제
        del verification_codes[key]
        
        return {"message": "비밀번호가 변경되었습니다."}
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"비밀번호 변경 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/user/change-plan")
async def change_user_plan(data: dict):
    """사용자 플랜 변경 (결제 기능)"""
    print(f"플랜 변경 요청 받음: {data}")
    try:
        user_id = data.get('user_id')
        new_plan = data.get('new_plan')
        
        print(f"user_id: {user_id}, new_plan: {new_plan}")
        
        if not user_id or not new_plan:
            raise HTTPException(status_code=400, detail="필수 정보가 누락되었습니다.")
        
        # 플랜 유효성 검사
        valid_plans = ['free', 'sentinel', 'pentera', 'premium']
        if new_plan not in valid_plans:
            raise HTTPException(status_code=400, detail="유효하지 않은 플랜입니다.")
        
        # 플랜 업데이트
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET plan = ? WHERE id = ?", (new_plan, user_id))
        conn.commit()
        
        print(f"플랜 업데이트 완료: user_id={user_id}, plan={new_plan}")
        
        # 업데이트된 사용자 정보 가져오기
        cursor.execute("SELECT id, name, username, email, phone, plan FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            print(f"사용자 정보 반환: {user}")
            return {
                "message": "플랜이 변경되었습니다.",
                "user": {
                    "id": user[0],
                    "name": user[1],
                    "username": user[2],
                    "email": user[3],
                    "phone": user[4],
                    "plan": user[5]
                }
            }
        else:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"플랜 변경 오류: {e}")
        raise HTTPException(status_code=500, detail="플랜 변경 중 오류가 발생했습니다.")


# ==================== 관리자 API ====================

@app.get("/api/admin/stats")
async def get_admin_stats():
    """관리자 대시보드 통계"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # 전체 사용자 수
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        
        # 전체 검사 수
        cursor.execute("SELECT COUNT(*) FROM scan_history")
        total_scans = cursor.fetchone()[0]
        
        # 유료 사용자 수 (free가 아닌 사용자)
        cursor.execute("SELECT COUNT(*) FROM users WHERE plan != 'free'")
        premium_users = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "total_users": total_users,
            "total_scans": total_scans,
            "premium_users": premium_users
        }
    
    except Exception as e:
        print(f"통계 조회 오류: {e}")
        raise HTTPException(status_code=500, detail="통계 조회 중 오류가 발생했습니다.")


@app.get("/api/admin/users")
async def get_all_users():
    """전체 사용자 목록 조회"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # 사용자 정보 + 검사 수 조회
        cursor.execute("""
            SELECT 
                u.id, u.name, u.username, u.email, u.plan, u.created_at,
                COUNT(s.id) as scan_count
            FROM users u
            LEFT JOIN scan_history s ON u.id = s.user_id
            GROUP BY u.id
            ORDER BY u.id ASC
        """)
        
        users = cursor.fetchall()
        conn.close()
        
        return {
            "users": [
                {
                    "id": user[0],
                    "name": user[1],
                    "username": user[2],
                    "email": user[3],
                    "plan": user[4] or 'free',
                    "created_at": user[5],
                    "scan_count": user[6]
                }
                for user in users
            ]
        }
    
    except Exception as e:
        print(f"사용자 목록 조회 오류: {e}")
        raise HTTPException(status_code=500, detail="사용자 목록 조회 중 오류가 발생했습니다.")


@app.put("/api/admin/user/{user_id}/plan")
async def change_user_plan(user_id: int, request: Request):
    """사용자 플랜 변경"""
    try:
        data = await request.json()
        new_plan = data.get('plan')
        
        if new_plan not in ['free', 'sentinel', 'pentera', 'premium']:
            raise HTTPException(status_code=400, detail="잘못된 플랜입니다.")
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute("UPDATE users SET plan = ? WHERE id = ?", (new_plan, user_id))
        conn.commit()
        conn.close()
        
        return {"message": "플랜이 변경되었습니다."}
    
    except Exception as e:
        print(f"플랜 변경 오류: {e}")
        raise HTTPException(status_code=500, detail="플랜 변경 중 오류가 발생했습니다.")


@app.delete("/api/admin/user/{user_id}")
async def delete_user_by_admin(user_id: int):
    """관리자가 사용자 삭제"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # 사용자 검사 이력 삭제
        cursor.execute("DELETE FROM scan_history WHERE user_id = ?", (user_id,))
        
        # 사용자 삭제
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        
        conn.commit()
        conn.close()
        
        return {"message": "사용자가 삭제되었습니다."}
    
    except Exception as e:
        print(f"사용자 삭제 오류: {e}")
        raise HTTPException(status_code=500, detail="사용자 삭제 중 오류가 발생했습니다.")

@app.delete("/api/admin/user/{user_id}/clear-scans")
async def clear_user_scan_history(user_id: int):
    """특정 사용자의 검사 내역 초기화"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # 해당 사용자의 모든 검사 이력 삭제
        cursor.execute("DELETE FROM scan_history WHERE user_id = ?", (user_id,))
        deleted_count = cursor.rowcount
        
        # 사용자의 scan_count를 0으로 리셋
        cursor.execute("UPDATE users SET scan_count = 0 WHERE id = ?", (user_id,))
        
        conn.commit()
        conn.close()
        
        print(f"사용자 {user_id}의 검사 이력 {deleted_count}개 삭제 및 scan_count 리셋")
        
        return {
            "message": "검사 내역이 초기화되었습니다.",
            "deleted_count": deleted_count
        }
    
    except Exception as e:
        print(f"검사 내역 초기화 오류: {e}")
        raise HTTPException(status_code=500, detail="검사 내역 초기화 중 오류가 발생했습니다.")


# ==================== 비밀번호 찾기 ====================

@app.post("/api/auth/verify-email")
async def verify_email(data: dict):
    """이메일 확인 (비밀번호 찾기용 - 아이디와 이메일 일치 확인)"""
    username = data.get("username")
    email = data.get("email")
    
    if not email:
        raise HTTPException(status_code=400, detail="이메일을 입력해주세요.")
    
    # username이 제공된 경우 (비밀번호 찾기)
    if username:
        try:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            
            cursor.execute("SELECT id, name FROM users WHERE username = ? AND email = ?", (username, email))
            user = cursor.fetchone()
            conn.close()
            
            if not user:
                raise HTTPException(status_code=404, detail="아이디와 이메일이 일치하지 않습니다.")
            
            return {
                "message": "아이디와 이메일이 확인되었습니다.",
                "user_id": user[0],
                "name": user[1]
            }
        
        except HTTPException:
            raise
        except Exception as e:
            print(f"사용자 확인 오류: {e}")
            raise HTTPException(status_code=500, detail="서버 오류가 발생했습니다.")
    
    # username이 없는 경우 (기존 이메일만 확인)
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, name FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        conn.close()
        
        if not user:
            raise HTTPException(status_code=404, detail="등록되지 않은 이메일입니다.")
        
        return {
            "message": "이메일이 확인되었습니다.",
            "user_id": user[0],
            "name": user[1]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"이메일 확인 오류: {e}")
        raise HTTPException(status_code=500, detail="이메일 확인 중 오류가 발생했습니다.")


@app.post("/api/auth/reset-password")
async def reset_password(data: dict):
    """비밀번호 재설정"""
    email = data.get("email")
    new_password = data.get("new_password")
    
    if not email or not new_password:
        raise HTTPException(status_code=400, detail="이메일과 새 비밀번호를 입력해주세요.")
    
    if len(new_password) < 6:
        raise HTTPException(status_code=400, detail="비밀번호는 최소 6자 이상이어야 합니다.")
    
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # 사용자 존재 확인
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        
        if not user:
            conn.close()
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
        
        # 비밀번호 해시화
        password_hash = hashlib.sha256(new_password.encode()).hexdigest()
        
        # 비밀번호 업데이트
        cursor.execute(
            "UPDATE users SET password_hash = ? WHERE email = ?",
            (password_hash, email)
        )
        
        conn.commit()
        conn.close()
        
        return {"message": "비밀번호가 성공적으로 변경되었습니다."}
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"비밀번호 재설정 오류: {e}")
        raise HTTPException(status_code=500, detail="비밀번호 재설정 중 오류가 발생했습니다.")


if __name__ == "__main__":
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║     보안 취약점 분석 대시보드 서버 시작                   ║
    ╠═══════════════════════════════════════════════════════════╣
    ║  URL: http://localhost:5050                               ║
    ║  API 문서: http://localhost:5050/docs                     ║
    ╚═══════════════════════════════════════════════════════════╝
    """)
    
    uvicorn.run("app:app", host="0.0.0.0", port=5050, reload=False)
