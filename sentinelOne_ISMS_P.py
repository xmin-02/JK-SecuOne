#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF → ISMS-P 감사 통합 파이프라인
PDF를 받으면 자동으로 OCR 추출 후 ISMS-P 준수성 감사까지 수행
"""
import sys
import json
import re
import csv
import hashlib
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime


# ============================================================================
# 섹션 1: PDF 추출 (pdf_ocr_extract_fixed)
# ============================================================================

def find_tesseract_cmd() -> str:
    """Tesseract 설치 경로 찾기"""
    candidates = [
        Path(r"C:/Program Files/Tesseract-OCR/tesseract.exe"),
        Path(r"C:/Program Files (x86)/Tesseract-OCR/tesseract.exe"),
        Path(r"C:/ProgramData/chocolatey/bin/tesseract.exe"),
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    import shutil
    t = shutil.which("tesseract")
    if t:
        return t
    return ""


def extract_text_native(pdf_path: Path) -> List[str]:
    """PyPDF2로 원본 텍스트 추출"""
    try:
        from PyPDF2 import PdfReader
    except Exception as e:
        raise RuntimeError("Missing PyPDF2: pip install PyPDF2") from e
    reader = PdfReader(str(pdf_path))
    pages = []
    for p in reader.pages:
        try:
            t = p.extract_text() or ""
        except Exception:
            t = ""
        pages.append(t)
    return pages


def needs_ocr(page_text: str, threshold_chars: int = 80) -> bool:
    """OCR 필요 판단"""
    if not page_text:
        return True
    if len(page_text.strip()) < threshold_chars:
        return True
    return False


def extract_text_with_ocr_fallback(pdf_path: Path, lang: str = "kor+eng", dpi: int = 150) -> List[str]:
    """PyPDF2 → PyMuPDF + OCR 폴백 (poppler 불필요)"""
    native_pages = extract_text_native(pdf_path)
    
    pages_needing_ocr = [i for i, p in enumerate(native_pages) if needs_ocr(p)]
    if not pages_needing_ocr:
        return native_pages
    
    print(f"[INFO] {len(pages_needing_ocr)}/{len(native_pages)} 페이지 OCR 처리 중...", file=sys.stderr)
    
    # PyMuPDF로 PDF 페이지를 이미지로 변환 (poppler 불필요)
    try:
        import fitz
        doc = fitz.open(str(pdf_path))
    except Exception as e:
        print(f"[WARN] PDF 변환 실패: {e}. native만 사용합니다.", file=sys.stderr)
        return native_pages
    
    tcmd = find_tesseract_cmd()
    
    for page_idx in pages_needing_ocr:
        try:
            page = doc[page_idx]
            # 이미지로 렌더링 (zoom으로 해상도 조절)
            mat = fitz.Matrix(dpi / 72, dpi / 72)
            pix = page.get_pixmap(matrix=mat)
            img = pix
            
            ocr_text = ""
            
            # Tesseract 시도
            if tcmd:
                try:
                    import pytesseract
                    from PIL import Image
                    import io
                    
                    pytesseract.pytesseract.tesseract_cmd = tcmd
                    
                    # fitz pixmap을 PIL Image로 변환
                    img_data = img.tobytes("ppm")
                    pil_img = Image.open(io.BytesIO(img_data))
                    
                    ocr_text = pytesseract.image_to_string(pil_img, lang=lang)
                    if ocr_text.strip():
                        native_pages[page_idx] = ocr_text
                        continue
                except Exception:
                    pass
            
            # EasyOCR 폴백
            try:
                import easyocr
                import numpy as np
                from PIL import Image
                import io
                
                langs = ["ko", "en"]
                reader = easyocr.Reader(langs, verbose=False, gpu=False)
                
                # fitz pixmap을 numpy array로 변환
                img_data = img.tobytes("ppm")
                pil_img = Image.open(io.BytesIO(img_data))
                img_array = np.array(pil_img)
                
                result = reader.readtext(img_array)
                ocr_text = "\n".join([text for (_, text, _) in result]) if result else ""
                
                if ocr_text.strip():
                    native_pages[page_idx] = ocr_text
            except Exception as e:
                print(f"[WARN] OCR 실패 (페이지 {page_idx+1}): {e}", file=sys.stderr)
        
        except Exception as e:
            print(f"[WARN] 페이지 {page_idx+1} 처리 실패: {e}", file=sys.stderr)
    
    doc.close()
    return native_pages


def pdf_to_ocr_json(pdf_path: Path, lang: str = "kor+eng", dpi: int = 300) -> dict:
    """PDF → OCR JSON 구조로 변환 (EasyOCR 우선, 빠르고 정확)"""
    print(f"[INFO] PDF 페이지 추출 중 ({lang}, {dpi}dpi)...", file=sys.stderr)
    
    try:
        import fitz
        doc = fitz.open(str(pdf_path))
        total_pages = len(doc)
        print(f"[INFO] 총 {total_pages}개 페이지 감지", file=sys.stderr)
    except Exception as e:
        print(f"[ERROR] PDF 열기 실패: {e}", file=sys.stderr)
        raise
    
    pages = []
    
    # EasyOCR 초기화 (한 번만)
    easy_reader = None
    try:
        import easyocr
        langs = ["ko", "en"]
        easy_reader = easyocr.Reader(langs, verbose=False, gpu=False)
        print(f"[INFO] EasyOCR 초기화 완료", file=sys.stderr)
    except Exception as e:
        print(f"[WARN] EasyOCR 초기화 실패: {e}, Tesseract 사용", file=sys.stderr)
    
    for page_num in range(total_pages):
        print(f"[INFO] 페이지 {page_num+1}: OCR 처리 중...", file=sys.stderr)
        
        try:
            page = doc[page_num]
            
            # 페이지를 이미지로 변환
            mat = fitz.Matrix(dpi / 72, dpi / 72)
            pix = page.get_pixmap(matrix=mat)
            
            ocr_text = ""
            
            # EasyOCR 시도 (우선순위 1)
            if easy_reader:
                try:
                    import numpy as np
                    from PIL import Image
                    import io
                    
                    print(f"[INFO] EasyOCR 시작 (한 번만 로드됨)...", file=sys.stderr)
                    
                    # fitz pixmap을 numpy array로 변환
                    img_data = pix.tobytes("ppm")
                    pil_img = Image.open(io.BytesIO(img_data))
                    img_array = np.array(pil_img)
                    
                    result = easy_reader.readtext(img_array)
                    ocr_text = "\n".join([text for (_, text, _) in result]) if result else ""
                    
                    if ocr_text.strip():
                        print(f"[OK] 페이지 {page_num+1}: EasyOCR ({len(ocr_text)}자)", file=sys.stderr)
                        pages.append(ocr_text)
                        continue
                except Exception as e:
                    print(f"[WARN] EasyOCR 실패: {e}", file=sys.stderr)
            
            # Tesseract 폴백 (우선순위 2)
            try:
                import pytesseract
                from PIL import Image
                import io
                
                tcmd = find_tesseract_cmd()
                if tcmd:
                    pytesseract.pytesseract.tesseract_cmd = tcmd
                    img_data = pix.tobytes("ppm")
                    pil_img = Image.open(io.BytesIO(img_data))
                    ocr_text = pytesseract.image_to_string(pil_img, lang=lang)
                    if ocr_text.strip():
                        print(f"[OK] 페이지 {page_num+1}: Tesseract OCR ({len(ocr_text)}자)", file=sys.stderr)
                        pages.append(ocr_text)
                        continue
            except Exception as e:
                print(f"[WARN] Tesseract 실패: {e}", file=sys.stderr)
            
            # 모든 OCR 실패
            print(f"[ERROR] 페이지 {page_num+1}: OCR 실패", file=sys.stderr)
            pages.append("")
        
        except Exception as e:
            print(f"[ERROR] 페이지 {page_num+1} 처리 실패: {e}", file=sys.stderr)
            pages.append("")
    
    doc.close()
    
    ocr_json = {
        "source_pdf": str(pdf_path),
        "generated_at": datetime.now().isoformat() + "Z",
        "pages": [{"page_num": i + 1, "text": text} for i, text in enumerate(pages)],
    }
    
    return ocr_json


# ============================================================================
# 섹션 2: OCR 파싱 (ocr_to_threats_parser)
# ============================================================================

def extract_all_text(ocr_json: dict) -> str:
    """OCR JSON에서 모든 텍스트 추출"""
    all_text = ""
    if "pages" in ocr_json:
        for page in ocr_json["pages"]:
            all_text += page.get("text", "") + "\n"
    
    # 디버깅: 추출된 텍스트 길이 출력
    print(f"[DEBUG] 총 추출된 텍스트 길이: {len(all_text)}자", file=sys.stderr)
    if len(all_text) > 0:
        preview = all_text[:200].replace('\n', ' ')
        print(f"[DEBUG] 텍스트 미리보기: {preview}...", file=sys.stderr)
    
    return all_text


def parse_threat_count(text: str) -> int:
    """총 위협 수 추출"""
    # 0건 패턴 먼저 체크
    zero_patterns = [
        r'No\s+Active\s+threats',
        r'No\s+Suspicious\s+activities',
        r'0\s+THREATS?\s+FOUND',
        r'THREATS?\s+FOUND[:\s]+0',
        r'Total\s+threats?[:\s]+0',
    ]
    
    for pattern in zero_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            print(f"[DEBUG] 위협 0건 감지 (패턴: {pattern})", file=sys.stderr)
            return 0
    
    # 위협 수 패턴
    count_patterns = [
        r'(\d+)\s+THREATS?\s+FOUND',
        r'Total\s+threats?[:\s]+(\d+)',
        r'THREATS?\s+FOUND[:\s]+(\d+)',
        r'^(\d+)\s*\n\s*Threats found',
        r'Active\s+threats?[:\s]+(\d+)',
        r'(\d+)\s+Active\s+threats?',
    ]
    
    for pattern in count_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            count = int(match.group(1))
            print(f"[DEBUG] 위협 수 감지: {count}건 (패턴: {pattern})", file=sys.stderr)
            return count
    
    print(f"[WARN] 위협 수 패턴을 찾을 수 없습니다", file=sys.stderr)
    return 0


def parse_mitigated_count(text: str) -> tuple:
    """완화된 위협 수와 미완화 위협 수 추출"""
    mitigated_matches = []
    not_mitigated_matches = []

    # Mitigated 패턴 (더 유연하게)
    patterns_mitigated = [
        r'(\d+)\s+Mitigated',
        r'Mitigated[:\s]+(\d+)',
        r'(\d+)\s+Manually Mitigated Threats',
        r'(\d+)\s+Automatically Mitigated Threats',
        r'@\s*\d+%\s*\|\s*(\d+)\s+Manually Mitigated',
        r'(\d+)\s+@\s*[\d.]+%\s*\|\s*Mitigated',  # 추가
    ]
    for pattern in patterns_mitigated:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            mitigated_matches.append(int(match.group(1)))

    # Not mitigated 패턴 (줄바꿈 허용)
    patterns_not_mitigated = [
        r'(\d+)\s+Not\s+mitigated',
        r'Not\s+mitigated[:\s]+(\d+)',
        r'(\d+)\s+Not\s+Mitigated\s+threats',
        r'No\s*\n?\s*Not\s*\n?\s*mitigated',  # "No\nNot\nmitigated" 허용
        r'([0-9]+)\s*(?:No\s*)?Not\s+mitigated',  # "0 No Not mitigated" 등
    ]
    for pattern in patterns_not_mitigated:
        for match in re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE):
            try:
                # 그룹이 있으면 추출
                if match.groups():
                    val = int(match.group(1))
                    not_mitigated_matches.append(val)
            except (ValueError, IndexError):
                # 숫자가 없는 패턴의 경우 (예: "No Not mitigated")
                # 이 경우 0으로 간주
                not_mitigated_matches.append(0)

    mitigated = max(mitigated_matches) if mitigated_matches else 0
    not_mitigated = max(not_mitigated_matches) if not_mitigated_matches else 0

    return mitigated, not_mitigated


def parse_classifications(text: str) -> Dict[str, int]:
    """위협 분류별 개수 추출"""
    classifications = {}
    
    section_match = re.search(r'CLASSIFICATIONS(.*?)(?:DETECTION BY|TOP DEVICES|$)', text, re.IGNORECASE | re.DOTALL)
    if section_match:
        section_text = section_match.group(1)
        
        patterns = [
            r'(\d+)\s+(General|Malware|Ransomware|Trojan|Suspicious|PUP)',
            r'@\s*[\d.]+%\s*\|\s*(\d+)\s+(General|Malware|Ransomware|Trojan|Suspicious|PUP)',
        ]
        
        for pattern in patterns:
            for match in re.finditer(pattern, section_text, re.IGNORECASE):
                count = int(match.group(1))
                classification = match.group(2).lower()
                if classification not in classifications:
                    classifications[classification] = count
    
    return classifications


def parse_devices(text: str) -> List[str]:
    """상위 위험 기기 추출"""
    devices = []
    
    section_match = re.search(r'TOP DEVICES AT RISK(.*?)(?:TOP GROUPS|TOP SITES|POLICY MODE|$)', text, re.IGNORECASE | re.DOTALL)
    section_text = section_match.group(1) if section_match else text
    
    patterns = [
        r'^\s*([A-Za-z0-9._\-]{2,})\s+\d+\s+\d+\s*$',
        r'Most at[-\s]risk device\s*\n\s*([A-Za-z0-9._\-]{2,})',
    ]
    
    for pat in patterns:
        for m in re.finditer(pat, section_text, re.MULTILINE | re.IGNORECASE):
            device = m.group(1).strip()
            if device.upper() in {"NAME", "THREATS", "UNIQUE", "HORE"}:
                continue
            devices.append(device)
    
    if not devices:
        for m in re.finditer(r'^\s*([A-Za-z0-9._\-]{3,})\s+\d+\s+\d+\s*$', text, re.MULTILINE):
            device = m.group(1).strip()
            if device.upper() in {"NAME", "THREATS", "UNIQUE", "HORE"}:
                continue
            devices.append(device)
    
    return list(dict.fromkeys(devices))[:10]


def generate_threat_items(
    total_count: int,
    mitigated_count: int,
    classifications: Dict[str, int],
    devices: List[str],
    report_date: Optional[str] = None
) -> List[Dict]:
    """통계 정보를 기반으로 위협 항목 생성"""
    threats = []
    threat_id = 1

    mitigated_count = max(0, min(mitigated_count, total_count))
    
    if not report_date:
        report_date = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    
    for classification, count in classifications.items():
        for i in range(count):
            is_mitigated = (threat_id <= mitigated_count)
            device = devices[i % len(devices)] if devices else "Unknown-Device"
            
            threat_signature = f"{classification}-{device}-{threat_id}"
            sha1_hash = hashlib.sha1(threat_signature.encode()).hexdigest()
            
            threat = {
                "id": str(threat_id),
                "name": f"{classification.capitalize()}.Generic.Item{i+1}",
                "classification": classification.capitalize(),
                "status": "Mitigated" if is_mitigated else "Active",
                "agent_name": device,
                "device_name": device,
                "user": None,
                "detected_at": report_date,
                "mitigated_at": report_date if is_mitigated else None,
                "remediated": is_mitigated,
                "confidence_level": 0.85,
                "severity": "High" if classification in ["ransomware", "trojan"] else "Medium",
                "sha1": sha1_hash,
                "file_hash": sha1_hash[:16],
            }
            
            threats.append(threat)
            threat_id += 1
    
    remaining = total_count - len(threats)
    for i in range(remaining):
        is_mitigated = (threat_id <= mitigated_count)
        device = devices[i % len(devices)] if devices else "Unknown-Device"
        
        threat_signature = f"general-{device}-{threat_id}"
        sha1_hash = hashlib.sha1(threat_signature.encode()).hexdigest()
        
        threat = {
            "id": str(threat_id),
            "name": f"General.Unknown.Item{i+1}",
            "classification": "General",
            "status": "Mitigated" if is_mitigated else "Active",
            "agent_name": device,
            "device_name": device,
            "user": None,
            "detected_at": report_date,
            "mitigated_at": report_date if is_mitigated else None,
            "remediated": is_mitigated,
            "confidence_level": 0.70,
            "severity": "Low",
            "sha1": sha1_hash,
            "file_hash": sha1_hash[:16],
        }
        
        threats.append(threat)
        threat_id += 1
    
    return threats


# ============================================================================
# 섹션 3: ISMS-P 분석 (isms_p_analyzer_v2)
# ============================================================================

# ISMS-P 인증기준 (정보보호 및 개인정보보호 관리체계 인증 등에 관한 고시)
ISMS_P_CONTROLS = {
    "2.7.1": {"category": "침해사고 관리", "title": "침해사고 예방 및 대응"},
    "2.7.2": {"category": "침해사고 관리", "title": "침해사고 대응 및 복구"},
    "2.8.4": {"category": "시스템 및 서비스 보안관리", "title": "악성코드 통제"},
    "2.8.5": {"category": "시스템 및 서비스 보안관리", "title": "시스템 침입 탐지 및 차단"},
    "2.3.1": {"category": "접근통제", "title": "사용자 계정 관리"},
    "2.3.2": {"category": "접근통제", "title": "사용자 인증"},
    "2.3.3": {"category": "접근통제", "title": "사용자 접근 관리"},
    "2.9.1": {"category": "암호화 적용", "title": "암호정책 수립 및 이행"},
    "2.9.2": {"category": "암호화 적용", "title": "암호키 관리"},
    "2.11.1": {"category": "재해 복구", "title": "백업 및 복구"},
    "2.11.2": {"category": "재해 복구", "title": "정보시스템 이중화"},
}

# SentinelOne 위협 유형별 ISMS-P 인증기준 매핑
THREAT_CLASSIFICATION_MAPPING = {
    "malware": ["2.8.4", "2.7.1", "2.7.2"],  # 악성코드 통제, 사고 예방 및 대응
    "ransomware": ["2.8.4", "2.7.1", "2.7.2", "2.11.1", "2.9.1"],  # + 백업/복구, 암호정책
    "trojan": ["2.8.4", "2.8.5", "2.3.3", "2.7.2"],  # + 침입탐지, 접근관리
    "suspicious": ["2.8.5", "2.7.1", "2.3.3"],  # 침입탐지, 사고예방, 접근관리
    "general": ["2.7.2", "2.8.4"],  # 사고대응, 악성코드 통제
    "pup": ["2.3.3", "2.8.4"],  # 접근관리, 악성코드 통제
}


@dataclass
class ThreatAnalysis:
    """위협 분석 결과"""
    threat_name: str
    classification: str
    device_name: str
    status: str
    isms_controls: List[str]
    violation_status: str
    confidence: float
    file_hash: Optional[str] = None
    sha1: Optional[str] = None


def safe_get(obj: Dict, *keys, default="") -> str:
    """안전한 딕셔너리 값 추출"""
    if not isinstance(obj, dict):
        return default
    for key in keys:
        value = obj.get(key)
        if value is not None and value != "":
            return str(value)
    return default


def extract_threat_classification(threat_name: str, explicit: Optional[str] = None) -> str:
    """위협명에서 분류 추출"""
    if explicit:
        explicit_norm = explicit.strip().lower()
        alias_map = {"malicious": "malware", "virus": "malware"}
        if explicit_norm in alias_map:
            return alias_map[explicit_norm]
        if explicit_norm in THREAT_CLASSIFICATION_MAPPING:
            return explicit_norm

    threat_lower = threat_name.lower()
    for classification in THREAT_CLASSIFICATION_MAPPING.keys():
        if classification in threat_lower:
            return classification
    return "general"


def extract_threat_status(threat_data: Dict) -> str:
    """위협 상태 판정"""
    status = safe_get(threat_data, "status", "threatStatus").lower()
    remediated_fields = [threat_data.get("remediated"), threat_data.get("mitigated")]
    
    if any(remediated_fields) or "mitigat" in status or "remedi" in status:
        return "Mitigated"
    if "active" in status or "pending" in status:
        return "Active"
    return "In Progress"


def map_threat_to_controls(threat_data: Dict) -> List[str]:
    """위협을 ISMS-P 제어로 매핑"""
    threat_name = safe_get(threat_data, "name", "threatName").lower()
    classification_field = safe_get(threat_data, "classification", "Classification", default="")
    classification = extract_threat_classification(threat_name, classification_field)
    
    controls = THREAT_CLASSIFICATION_MAPPING.get(classification, ["2.7.2"])
    
    if "ransomware" in threat_name or classification == "ransomware":
        controls.extend(["2.11.1", "2.11.2"])  # 랜섬웨어는 백업/이중화 필수
    
    return sorted(list(set(controls)))


def analyze_threat(threat_data: Dict) -> ThreatAnalysis:
    """개별 위협 분석"""
    threat_name = safe_get(threat_data, "name", "threatName", default="Unknown")
    classification_field = safe_get(threat_data, "classification", "Classification", default="")
    classification = extract_threat_classification(threat_name, classification_field)
    
    device_name = safe_get(
        threat_data, 
        "agent_name", "agentName", "deviceName", "device_name",
        default="Unknown"
    )
    
    status = extract_threat_status(threat_data)
    isms_controls = map_threat_to_controls(threat_data)
    
    violation_status = "완화" if status == "Mitigated" else "위반" if status == "Active" else "조치중"
    confidence = float(safe_get(threat_data, "confidence_level", default="0") or 0)
    
    # 해시 값 추출
    file_hash = safe_get(threat_data, "file_hash", "fileHash", "hash", default=None) or None
    sha1 = safe_get(threat_data, "sha1", "SHA1", "sha1Hash", default=None) or None
    
    return ThreatAnalysis(
        threat_name=threat_name,
        classification=classification,
        device_name=device_name,
        status=status,
        isms_controls=isms_controls,
        violation_status=violation_status,
        confidence=confidence,
        file_hash=file_hash,
        sha1=sha1,
    )


def extract_threats_from_json(report_data: dict) -> List[Dict]:
    """JSON에서 위협 데이터 추출"""
    if not isinstance(report_data, dict):
        return []
    
    for key in ["threats", "Threats", "items", "data", "payload"]:
        if key in report_data and isinstance(report_data[key], list):
            value = report_data[key]
            if value and isinstance(value[0], dict):
                if any(k in value[0] for k in ["name", "threatName"]):
                    return value
    
    return []


def parse_threats_csv(csv_path: Path) -> List[Dict]:
    """SentinelOne threats CSV를 표준 위협 딕셔너리 리스트로 변환"""
    threats: List[Dict] = []

    with open(csv_path, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            status_text = (row.get("Status") or "").strip().lower()
            mitigated = status_text.startswith("mitigated")

            classification_raw = (row.get("Classification") or "general").strip()

            # confidence_level 안전 변환
            conf_val = row.get("Confidence Level", "0")
            try:
                confidence = float(conf_val or 0)
            except (ValueError, TypeError):
                confidence = 0.0

            threat = {
                "name": row.get("Threat Details") or row.get("Threat") or "Unknown",
                "classification": classification_raw,
                "status": "Mitigated" if mitigated else "Active",
                "agent_name": row.get("Endpoints") or row.get("Agent") or row.get("Site") or "Unknown",
                "device_name": row.get("Endpoints") or row.get("Group") or "Unknown",
                "detected_at": row.get("Identifying Time (UTC)") or row.get("Reported Time (UTC)") or None,
                "mitigated_at": row.get("Reported Time (UTC)") if mitigated else None,
                "remediated": mitigated,
                "confidence_level": confidence,
                "sha1": row.get("Hash") or None,
                "file_hash": row.get("Hash") or None,
            }

            # Incident status 보조 적용
            incident_status = (row.get("Incident Status") or "").lower()
            if not mitigated and "not mitigated" in incident_status:
                threat["status"] = "Active"

            threats.append(threat)

    return threats


def calculate_stats(analyses):
    """통계 계산"""
    total = len(analyses)
    mitigated = sum(1 for a in analyses if a.status == "Mitigated")
    active = sum(1 for a in analyses if a.status == "Active")
    
    return {
        "total": total,
        "mitigated": mitigated,
        "active": active,
        "mitigation_rate": (mitigated / total * 100) if total > 0 else 0,
        "active_rate": (active / total * 100) if total > 0 else 0,
    }


def detect_report_target(text: str, fallback: str = "알 수 없음"):
    """보고서 텍스트에서 감사 대상 추출"""
    email_match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', text)
    user_field = re.search(r'User[:\-]\s*([^\n]+)', text, re.IGNORECASE)
    if email_match:
        return "개인", email_match.group(1).strip(), "email"
    if user_field:
        return "개인", user_field.group(1).strip(), "user-field"

    group_patterns = [
        r'Group[:\-]\s*([^\n]+)',
        r'Group\s+([A-Za-z0-9].+)',
        r'Most at[-\s]risk device\s*\n\s*([^\n]+)',
        r'Most at[-\s]risk user\s*\n\s*([^\n]+)',
        r'Tenant[:\-]\s*([^\n]+)',
        r'Account[:\-]\s*([^\n]+)',
    ]
    for pat in group_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return "그룹", m.group(1).strip(), pat

    return "그룹", fallback, "fallback"


CONTROL_DESCRIPTIONS = {
    "2.7.1": {"title": "침해사고 예방 및 대응", "action": "위협 탐지 및 즉시 대응 조치"},
    "2.7.2": {"title": "침해사고 대응 및 복구", "action": "사고 분류 및 복구 절차 이행"},
    "2.8.4": {"title": "악성코드 통제", "action": "악성코드 탐지·차단 및 제거"},
    "2.8.5": {"title": "시스템 침입 탐지 및 차단", "action": "침입 탐지 시스템 운영 및 차단"},
    "2.3.1": {"title": "사용자 계정 관리", "action": "계정 권한 검토 및 조정"},
    "2.3.2": {"title": "사용자 인증", "action": "인증 강화 및 통제"},
    "2.3.3": {"title": "사용자 접근 관리", "action": "접근권한 제한 및 모니터링"},
    "2.9.1": {"title": "암호정책 수립 및 이행", "action": "암호화 정책 적용 및 이행"},
    "2.9.2": {"title": "암호키 관리", "action": "암호키 생성·보관·폐기 관리"},
    "2.11.1": {"title": "백업 및 복구", "action": "백업 수행 및 복구 테스트"},
    "2.11.2": {"title": "정보시스템 이중화", "action": "시스템 이중화 및 가용성 확보"},
}


def print_report_console_ascii(analyses, stats, report_name, report_meta=None):
    """ASCII 안전 출력"""
    print(f"\n  [감사 결과]")
    
    if report_meta:
        if report_meta.get("type") == "그룹":
            print(f"  감사 대상: {report_meta.get('target', '알 수 없음')} 그룹")
        else:
            print(f"  감사 대상: {report_meta.get('target', '알 수 없음')} 사용자")
        
        if report_meta.get("devices"):
            print(f"  영향 기기: {len(report_meta['devices'])}대 ({', '.join(report_meta['devices'][:3])}...)")
    
    print(f"  위협 탐지: {stats['total']}건")
    print(f"  조치 완료: {stats['mitigated']}건 ({stats['mitigation_rate']:.1f}%)")
    print(f"  조치 필요: {stats['active']}건 ({stats['active_rate']:.1f}%)")
    
    control_map = {}
    for analysis in analyses:
        for control in analysis.isms_controls:
            if control not in control_map:
                control_map[control] = {"total": 0, "mitigated": 0, "classifications": []}
            control_map[control]["total"] += 1
            control_map[control]["classifications"].append(analysis.classification.lower())
            if analysis.status == "Mitigated":
                control_map[control]["mitigated"] += 1
    
    print(f"\n  [준수 항목 ({len(control_map)}개)]")
    
    for control, counts in sorted(control_map.items()):
        mitigation_rate = (counts["mitigated"] / counts["total"] * 100) if counts["total"] > 0 else 0
        status_icon = "[OK]" if mitigation_rate >= 80 else "[!]" if mitigation_rate >= 50 else "[X]"
        
        control_info = CONTROL_DESCRIPTIONS.get(control, {"title": control, "action": "조치"})
        
        classifications_list = counts.get("classifications", [])
        class_summary = {}
        for c in classifications_list:
            class_summary[c] = class_summary.get(c, 0) + 1
        
        threat_types = ", ".join([f"{k.upper()} {v}건" for k, v in class_summary.items()])
        
        print(f"\n    {status_icon} {control} {control_info['title']}")
        print(f"        탐지: 보고서에서 {threat_types} 발견")
        
        if mitigation_rate >= 80:
            print(f"        조치: {control_info['action']} 완료 ({counts['mitigated']}/{counts['total']}건, {mitigation_rate:.0f}%)")
        elif mitigation_rate >= 50:
            remaining = counts['total'] - counts['mitigated']
            print(f"        조치: 부분 완료 ({counts['mitigated']}/{counts['total']}건)")
            print(f"        필요: {remaining}건 추가 대응 필요 ({mitigation_rate:.0f}%)")
        else:
            print(f"        조치: 미실시 ({counts['mitigated']}/{counts['total']}건)")
            print(f"        필요: 즉시 {control_info['action']} 실시 필요 ({mitigation_rate:.0f}%)")
    
    if len(analyses) > 0:
        print(f"\n  [위협 상세 내역 (전체 {len(analyses)}건)]")
        
        for i, analysis in enumerate(analyses, 1):
            status_icon = "[OK]" if analysis.status == "Mitigated" else "[X]" if analysis.status == "Active" else "[!]"
            
            print(f"\n    {i}. {status_icon} {analysis.threat_name}")
            print(f"       분류: {analysis.classification.upper()} | 상태: {analysis.violation_status}")
            print(f"       기기: {analysis.device_name}")
            
            threat_hash = getattr(analysis, 'file_hash', None) or getattr(analysis, 'sha1', None)
            if threat_hash:
                print(f"       해시: {threat_hash}")
            
            print(f"       준수: {', '.join(analysis.isms_controls)}")
    
    print()


def print_final_summary(all_analyses):
    """복수 보고서의 최종 통합 요약"""
    if not all_analyses:
        return
    
    # 중복 제거
    dedup_map = {}
    deduped = []
    for a in all_analyses:
        threat_hash = getattr(a, "file_hash", None) or getattr(a, "sha1", None)
        if threat_hash:
            key = ("hash", str(threat_hash).lower())
        else:
            key = ("name-device", a.threat_name.lower(), a.device_name.lower())
        if key in dedup_map:
            continue
        dedup_map[key] = True
        deduped.append(a)
    
    stats = calculate_stats(deduped)
    
    print(f"  [최종 통합 요약]")
    print(f"{'='*70}\n")
    print(f"  [통합 지표]")
    if len(deduped) != len(all_analyses):
        print(f"  (중복 제거 적용: {len(all_analyses)}건 → {len(deduped)}건)")
    print(f"  총 위협 탐지: {stats['total']}건")
    print(f"  조치 완료: {stats['mitigated']}건 ({stats['mitigation_rate']:.1f}%)")
    print(f"  조치 필요: {stats['active']}건 ({stats['active_rate']:.1f}%)")
    
    control_map = {}
    for analysis in deduped:
        for control in analysis.isms_controls:
            if control not in control_map:
                control_map[control] = {"total": 0, "mitigated": 0, "active": 0}
            control_map[control]["total"] += 1
            if analysis.status == "Mitigated":
                control_map[control]["mitigated"] += 1
            elif analysis.status == "Active":
                control_map[control]["active"] += 1
    
    print(f"\n  [제어별 준수 현황]")
    
    critical_issues = []
    for control, counts in sorted(control_map.items()):
        mitigation_rate = (counts["mitigated"] / counts["total"] * 100) if counts["total"] > 0 else 0
        
        control_info = CONTROL_DESCRIPTIONS.get(control, {"title": control})
        print(f"    {control} {control_info['title']}")
        print(f"      영향 위협: {counts['total']}건 | 조치됨: {counts['mitigated']}건 | 미조치: {counts['active']}건 ({mitigation_rate:.0f}%)")
        
        if mitigation_rate < 80:
            critical_issues.append((control, counts['active']))
    
    if critical_issues:
        print(f"\n  [주의 - 80% 미만 제어]")
        for control, active_count in critical_issues:
            print(f"    {control}: {active_count}건 미조치")
    
    print(f"\n{'='*70}\n")


# ============================================================================
# 메인
# ============================================================================

def main():
    if len(sys.argv) < 2:
        print("사용법: python pdf_to_isms_audit.py <파일1.pdf> [파일2.pdf] ...")
        print("예시: python pdf_to_isms_audit.py Test5.pdf Test6.pdf")
        sys.exit(1)
    
    report_files = sys.argv[1:]
    all_analyses = []
    
    print("\n" + "=" * 70)
    print("  ISMS-P 준수성 감사")
    print(f"  대상 보고서: {len(report_files)}건")
    print("=" * 70)
    
    for idx, report_file in enumerate(report_files, 1):
        print(f"\n{'-'*70}")
        print(f"[보고서 {idx}/{len(report_files)}] {Path(report_file).name}")
        print(f"{'-'*70}")
        
        report_path = Path(report_file)
        if not report_path.exists():
            print(f"[ERROR] 파일 없음: {report_file}")
            continue
        
        try:
            # CSV 파일 처리
            if report_path.suffix.lower() == ".csv":
                threats = parse_threats_csv(report_path)

                if not threats:
                    print("  판정: CSV에서 위협을 찾지 못함")
                    continue

                threat_count = len(threats)
                mitigated = sum(1 for t in threats if str(t.get("status", "")).lower().startswith("mitigated") or t.get("remediated"))
                classifications = {}
                for t in threats:
                    cls = str(t.get("classification", "general")).strip().lower() or "general"
                    classifications[cls] = classifications.get(cls, 0) + 1

                devices = [t.get("device_name") for t in threats if t.get("device_name")]
                devices = list(dict.fromkeys(devices))[:10]

                analyses = [analyze_threat(t) for t in threats]
                stats = calculate_stats(analyses)

                report_meta = {
                    "type": "그룹",
                    "target": report_path.stem,
                    "devices": devices,
                }

                print(f"  유형: 그룹 보고서 ({report_path.stem})")
                print_report_console_ascii(analyses, stats, report_path.name, report_meta)
                all_analyses.extend(analyses)
                continue

            # PDF → OCR JSON 변환 (내장 OCR 사용)
            # 기존 OCR JSON 파일 확인
            ocr_dir = Path("ocr_output")
            ocr_filename = report_path.stem + ".json"
            ocr_json_path = ocr_dir / ocr_filename
            
            if ocr_json_path.exists():
                with open(ocr_json_path, "r", encoding="utf-8") as f:
                    ocr_json = json.load(f)
            else:
                # 내장 OCR 함수로 직접 처리
                ocr_dir.mkdir(exist_ok=True)
                ocr_json = pdf_to_ocr_json(report_path, lang="kor+eng", dpi=300)
                
                # JSON 저장
                with open(ocr_json_path, "w", encoding="utf-8") as f:
                    json.dump(ocr_json, f, ensure_ascii=False, indent=2)
                
                print(f"[INFO] OCR 결과 저장: {ocr_json_path}", file=sys.stderr)
            
            text = extract_all_text(ocr_json)
            
            # OCR 텍스트 파싱
            threat_count = parse_threat_count(text)
            mitigated, not_mitigated = parse_mitigated_count(text)
            classifications = parse_classifications(text)
            devices = parse_devices(text)
            
            if not classifications:
                classifications = {"general": threat_count}
            
            if threat_count == 0:
                print("  판정: 위협 없음 (적합)\n")
                continue
            
            # 위협 항목 생성 및 분석
            threat_items = generate_threat_items(threat_count, mitigated, classifications, devices)
            analyses = [analyze_threat(t) for t in threat_items]
            stats = calculate_stats(analyses)
            
            # 보고서 대상 추출
            report_type, report_target, _ = detect_report_target(text, report_path.stem)
            
            # 유형 출력 (백업본과 동일)
            print(f"  유형: {report_type} 보고서 ({report_target})")
            
            report_meta = {
                "type": report_type,
                "target": report_target,
                "pdf": str(report_path),
                "threat_count": threat_count,
                "devices": devices,
            }
            
            print_report_console_ascii(analyses, stats, report_path.name, report_meta)
            all_analyses.extend(analyses)
            
        except Exception as e:
            print(f"[ERROR] 분석 실패: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    if len(report_files) > 1 and all_analyses:
        print(f"\n{'='*70}")
        print_final_summary(all_analyses)


if __name__ == "__main__":
    main()
