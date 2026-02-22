"""
Pentera PDF OCR 및 ISMS-P 매칭 프로그램
PDF 파일에서 특정 내용을 추출하여 ISMS-P와 매칭하는 프로그램
"""

import re
from pathlib import Path
from typing import Optional, Dict, List
import argparse
import csv
import pytesseract
import fitz  # PyMuPDF
from PIL import Image
import io


class PenteraPDFExtractor:
    """Pentera PDF에서 특정 데이터를 추출하는 클래스"""
    
    def __init__(self, pdf_path: str):
        """
        Args:
            pdf_path: 처리할 PDF 파일 경로
        """
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF 파일을 찾을 수 없습니다: {pdf_path}")
        
        # Tesseract 경로 설정 (Windows 기본 경로)
        # 필요시 사용자 환경에 맞게 수정
        # pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    
    def extract_text_from_page(self, page_number: int, dpi: int = 300, use_ocr: bool = False) -> str:
        """
        특정 페이지의 텍스트를 추출 (텍스트 레이어 우선, 필요시 OCR)
        
        Args:
            page_number: 추출할 페이지 번호 (1-based)
            dpi: OCR 사용 시 이미지 변환 해상도
            use_ocr: True면 강제로 OCR 사용
            
        Returns:
            추출된 텍스트
        """
        print(f"페이지 {page_number} 처리 중...")
        
        try:
            # PDF 문서 열기
            pdf_document = fitz.open(self.pdf_path)
            
            # 페이지 인덱스는 0-based이므로 1을 빼줌
            page_index = page_number - 1
            
            if page_index >= len(pdf_document):
                pdf_document.close()
                return ""
            
            # 페이지 가져오기
            page = pdf_document[page_index]
            
            # 먼저 PDF의 텍스트 레이어에서 텍스트 추출 시도
            if not use_ocr:
                text = page.get_text()
                if text.strip():  # 텍스트가 있으면 반환
                    pdf_document.close()
                    print(f"  ✓ 텍스트 레이어에서 추출 성공")
                    return text
                else:
                    print(f"  ℹ 텍스트 레이어 없음, OCR 시도...")
            
            # 텍스트 레이어가 없거나 use_ocr=True인 경우 OCR 사용
            try:
                # 페이지를 이미지로 렌더링
                zoom = dpi / 72
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat)
                
                # PIL Image로 변환
                img_data = pix.tobytes("png")
                image = Image.open(io.BytesIO(img_data))
                
                pdf_document.close()
                
                # OCR로 텍스트 추출
                text = pytesseract.image_to_string(image, lang='eng')
                print(f"  ✓ OCR로 추출 성공")
                return text
                
            except Exception as ocr_error:
                pdf_document.close()
                print(f"  ✗ OCR 실패: {ocr_error}")
                print(f"  ℹ Tesseract OCR이 필요합니다. https://github.com/UB-Mannheim/tesseract/wiki")
                return ""
            
        except Exception as e:
            print(f"페이지 추출 오류: {e}")
            return ""
    
    def find_achievements_page(self, start_page: int = 2) -> Optional[int]:
        """
        Table of Contents에서 Achievements 항목의 페이지 번호를 찾음
        
        Args:
            start_page: 검색을 시작할 페이지 (기본값: 2)
            
        Returns:
            Achievements 페이지 번호, 찾지 못하면 None
        """
        print("\n=== Table of Contents에서 Achievements 페이지 찾기 ===")
        
        # 목차는 보통 처음 몇 페이지에 위치하므로 최대 10페이지까지만 검색
        max_toc_pages = 10
        
        for page_num in range(start_page, start_page + max_toc_pages):
            try:
                text = self.extract_text_from_page(page_num)
                
                # "Table Of Contents" 또는 "Table of Contents" 확인
                if re.search(r'table\s+of\s+contents', text, re.IGNORECASE):
                    print(f"✓ 목차 발견: 페이지 {page_num}")
                    
                    # Detailed Report 섹션 내의 Achievements 찾기
                    # 패턴: "Achievements" 뒤에 페이지 번호가 오는 형식
                    # 예: "Achievements ........ 15" 또는 "Achievements 15"
                    
                    # 여러 패턴 시도
                    patterns = [
                        r'Achievements[\s\.]+(\d+)',  # Achievements .... 15
                        r'Achievements.*?(\d+)',       # Achievements ... 15
                    ]
                    
                    for pattern in patterns:
                        matches = re.finditer(pattern, text, re.IGNORECASE)
                        for match in matches:
                            achievements_page = int(match.group(1))
                            print(f"✓ Achievements 페이지 발견: {achievements_page}")
                            return achievements_page
                    
                    # 같은 페이지 또는 다음 페이지에서 더 찾아보기
                    continue
                    
            except Exception as e:
                print(f"페이지 {page_num} 처리 중 오류: {e}")
                continue
        
        print("✗ Achievements 페이지를 찾지 못했습니다.")
        return None
    
    def find_end_page(self, start_page: int, end_marker: str = "MITRE ATT&CK Matrix for Enterprise") -> Optional[int]:
        """
        종료 마커가 나오는 페이지 찾기
        
        Args:
            start_page: 검색 시작 페이지
            end_marker: 종료를 나타내는 텍스트
            
        Returns:
            종료 마커가 나오는 페이지 번호, 찾지 못하면 None
        """
        print(f"\n=== '{end_marker}' 페이지 찾기 ===")
        
        # 최대 50페이지까지 검색
        max_search = 50
        
        for page_num in range(start_page, start_page + max_search):
            try:
                text = self.extract_text_from_page(page_num)
                
                if end_marker.lower() in text.lower():
                    print(f"✓ '{end_marker}' 발견: 페이지 {page_num}")
                    return page_num
                    
            except Exception as e:
                print(f"페이지 {page_num} 처리 중 오류: {e}")
                continue
        
        print(f"✗ '{end_marker}' 페이지를 찾지 못했습니다.")
        return None
    
    def extract_all_achievements(self, start_page: int, end_page: int) -> List[Dict[str, str]]:
        """
        여러 페이지에 걸쳐 있는 모든 Achievements 항목을 추출
        
        Args:
            start_page: 시작 페이지 번호
            end_page: 종료 페이지 번호 (해당 페이지는 포함하지 않음)
            
        Returns:
            추출된 데이터 리스트 [{'number': '#1', 'severity': '4.7', 'name': '...'}, ...]
        """
        print(f"\n=== 페이지 {start_page}부터 {end_page-1}까지 모든 Achievements 추출 ===")
        
        all_achievements = []
        
        for page_num in range(start_page, end_page):
            print(f"\n--- 페이지 {page_num} 처리 중 ---")
            
            text = self.extract_text_from_page(page_num)
            
            if not text:
                print(f"  ✗ 페이지 {page_num}에서 텍스트를 추출할 수 없습니다.")
                continue
            
            # 페이지별 항목 추출
            achievements = self._parse_achievements_from_text(text)
            
            if achievements:
                all_achievements.extend(achievements)
                print(f"  ✓ {len(achievements)}개 항목 발견")
            else:
                print(f"  ℹ 항목 없음")
        
        print(f"\n총 {len(all_achievements)}개 항목 추출 완료")
        return all_achievements
    
    def _parse_achievements_from_text(self, text: str) -> List[Dict[str, str]]:
        """
        텍스트에서 Achievements 항목 파싱
        
        Args:
            text: 파싱할 텍스트
            
        Returns:
            추출된 항목 리스트
        """
        achievements = []
        lines = text.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # #숫자 패턴 찾기
            if re.match(r'^#\d+$', line):
                number = line
                severity = None
                name = None
                
                # 다음 줄부터 severity와 name 찾기
                j = i + 1
                found_severity_keyword = False
                
                while j < len(lines) and j < i + 20:  # 최대 20줄 내에서 찾기
                    current_line = lines[j].strip()
                    
                    # severity 키워드 찾기
                    if current_line.lower() == 'severity':
                        found_severity_keyword = True
                        # severity 키워드 바로 위의 숫자가 severity 값
                        if j > 0:
                            potential_severity = lines[j-1].strip()
                            # 숫자인지 확인 (소수점 포함)
                            if re.match(r'^\d+\.?\d*$', potential_severity):
                                severity = potential_severity
                        j += 1
                        continue
                    
                    # severity 키워드 다음에 나오는 의미있는 텍스트가 이름
                    if found_severity_keyword and severity and current_line:
                        # 다음 #숫자가 나오기 전까지, 비어있지 않은 첫 줄이 이름
                        if not re.match(r'^#\d+$', current_line) and \
                           current_line.lower() not in ['remediation', 'priority', 'occurrences'] and \
                           not re.match(r'^\d+\s+occurrences?$', current_line):
                            name = current_line
                            break
                    
                    j += 1
                
                # 데이터가 모두 추출되었으면 추가
                if number and severity and name:
                    achievements.append({
                        'number': number,
                        'severity': severity,
                        'name': name
                    })
                
                i = j  # 다음 검색 위치로 이동
            else:
                i += 1
        
        return achievements
    
    def process(self) -> Optional[List[Dict]]:
        """
        전체 처리 프로세스 실행
        
        Returns:
            추출 결과 리스트
        """
        print(f"\n{'='*60}")
        print(f"PDF 파일 처리 시작: {self.pdf_path.name}")
        print(f"{'='*60}")
        
        # 1. Achievements 시작 페이지 찾기
        start_page = self.find_achievements_page()
        
        if start_page is None:
            print("\n처리 실패: Achievements 페이지를 찾을 수 없습니다.")
            return None
        
        # 2. 종료 페이지 찾기 (MITRE ATT&CK Matrix가 나오는 페이지)
        end_page = self.find_end_page(start_page)
        
        if end_page is None:
            # 종료 페이지를 못 찾으면 시작 페이지부터 +20 페이지까지만 처리
            print(f"\n⚠ 종료 마커를 찾지 못했습니다. 시작 페이지부터 20페이지까지 처리합니다.")
            end_page = start_page + 20
        
        # 3. 모든 항목 추출
        results = self.extract_all_achievements(start_page, end_page)
        
        if not results:
            print(f"\n처리 실패: Achievements 항목을 찾을 수 없습니다.")
            return None
        
        print(f"\n{'='*60}")
        print("처리 완료!")
        print(f"{'='*60}")
        
        return results


class ISMSPMapper:
    """Pentera 취약점과 ISMS-P 기준을 매핑하는 클래스"""
    
    def __init__(self, vulnerabilities_csv: str = "pentera_Vulnerabilities.csv", 
                 isms_csv: str = "ISMS_P.csv"):
        """
        Args:
            vulnerabilities_csv: Pentera 취약점 매핑 CSV 파일 경로
            isms_csv: ISMS-P 기준 CSV 파일 경로
        """
        self.vulnerabilities_csv = Path(vulnerabilities_csv)
        self.isms_csv = Path(isms_csv)
        
        if not self.vulnerabilities_csv.exists():
            raise FileNotFoundError(f"파일을 찾을 수 없습니다: {vulnerabilities_csv}")
        if not self.isms_csv.exists():
            raise FileNotFoundError(f"파일을 찾을 수 없습니다: {isms_csv}")
        
        # CSV 데이터 로드
        self.vulnerabilities_map = self._load_vulnerabilities_map()
        self.isms_data = self._load_isms_data()
    
    def _load_vulnerabilities_map(self) -> Dict[str, str]:
        """
        pentera_Vulnerabilities.csv 파일 로드
        
        Returns:
            취약점명 -> 번호 매핑 딕셔너리
        """
        mapping = {}
        
        with open(self.vulnerabilities_csv, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                vuln_name = row.get('Vulnerabilities', '').strip()
                number = row.get('number', '').strip()
                
                if vuln_name and number:
                    mapping[vuln_name] = number
        
        print(f"\n✓ {len(mapping)}개 취약점 매핑 로드 완료")
        return mapping
    
    def _load_isms_data(self) -> Dict[str, List[Dict]]:
        """
        ISMS_P.csv 파일 로드
        
        Returns:
            Pentera 번호 -> ISMS-P 항목 리스트 매핑 딕셔너리
        """
        mapping = {}
        last_category = ""  # 이전 분류 값 기억
        
        # 여러 인코딩 시도
        encodings = ['utf-8-sig', 'cp949', 'euc-kr', 'utf-8']
        
        for encoding in encodings:
            try:
                with open(self.isms_csv, 'r', encoding=encoding) as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        pentera_field = row.get('Pentera', '').strip()
                        category = row.get('분류', '').strip()
                        
                        # 분류가 비어있으면 이전 분류 사용
                        if category:
                            last_category = category
                        else:
                            category = last_category
                        
                        # Pentera 필드에 여러 번호가 쉼표로 구분되어 있을 수 있음 (예: #1,#3,#5)
                        if pentera_field and pentera_field != '#':
                            # 쉼표로 분리
                            numbers = [n.strip() for n in pentera_field.split(',')]
                            
                            for pentera_number in numbers:
                                if pentera_number and pentera_number != '#':
                                    if pentera_number not in mapping:
                                        mapping[pentera_number] = []
                                    
                                    mapping[pentera_number].append({
                                        '분류': category,
                                        '항목': row.get('항목', '').strip(),
                                        '인증기준': row.get('인증기준', '').strip(),
                                        '주요 확인사항': row.get('주요 확인사항', '').strip(),
                                        '관련 법규': row.get('관련 법규', '').strip(),
                                        '세부 설명': row.get('세부 설명', '').strip(),
                                        '미흡사례': row.get('미흡사례', '').strip(),
                                    })
                
                print(f"✓ {len(mapping)}개 Pentera 번호에 대한 ISMS-P 매핑 로드 완료 (인코딩: {encoding})")
                return mapping
            except (UnicodeDecodeError, Exception) as e:
                if encoding == encodings[-1]:  # 마지막 인코딩도 실패
                    print(f"⚠ ISMS-P CSV 파일 로드 실패: {e}")
                    return {}
                continue
        
        return mapping
    
    def find_vulnerability_number(self, vuln_name: str) -> Optional[str]:
        """
        취약점명으로 번호 찾기 (유연한 매칭)
        
        Args:
            vuln_name: 취약점명
            
        Returns:
            번호 (예: #1), 찾지 못하면 None
        """
        # 정규화 함수: 공백, 특수문자 제거 후 소문자 변환
        def normalize(s):
            # 모든 공백류 문자를 일반 공백으로 변경
            s = re.sub(r'\s+', ' ', s)
            # 앞뒤 공백 제거 후 소문자
            return s.strip().lower()
        
        vuln_name_normalized = normalize(vuln_name)
        
        # 1차: 정규화 후 정확 매칭
        for key, value in self.vulnerabilities_map.items():
            key_normalized = normalize(key)
            if key_normalized == vuln_name_normalized:
                return value
        
        # 2차: 부분 일치
        for key, value in self.vulnerabilities_map.items():
            key_normalized = normalize(key)
            if vuln_name_normalized in key_normalized or key_normalized in vuln_name_normalized:
                print(f"  → 유사 매칭: '{vuln_name}' ≈ '{key}' -> {value}")
                return value
        
        # 3차: 단어별 비교 (모든 주요 단어가 포함되어 있는지)
        vuln_words = set(vuln_name_normalized.split())
        for key, value in self.vulnerabilities_map.items():
            key_words = set(normalize(key).split())
            # 80% 이상의 단어가 일치하면 매칭
            if len(vuln_words) > 0:
                match_ratio = len(vuln_words & key_words) / len(vuln_words)
                if match_ratio >= 0.8:
                    return value
        
        return None
    
    def get_isms_violations(self, vuln_name: str) -> Optional[Dict]:
        """
        취약점명으로 ISMS-P 위반 항목 찾기
        
        Args:
            vuln_name: 취약점명
            
        Returns:
            {'number': '#1', 'violations': [...]} 형태의 딕셔너리
        """
        # 1. 취약점명으로 번호 찾기
        number = self.find_vulnerability_number(vuln_name)
        
        if number is None:
            return None
        
        # 2. 번호로 ISMS-P 항목 찾기
        violations = self.isms_data.get(number, [])
        
        if not violations:
            return None
        
        return {
            'number': number,
            'vulnerability': vuln_name,
            'violations': violations
        }
    
    def print_violation_report(self, vuln_name: str):
        """
        취약점에 대한 ISMS-P 위반 보고서 출력
        
        Args:
            vuln_name: 취약점명
        """
        result = self.get_isms_violations(vuln_name)
        
        if result is None:
            print(f"\n{'='*60}")
            print(f"⚠ 취약점 [{vuln_name}]에 대한 ISMS-P 매핑을 찾을 수 없습니다.")
            print("="*60)
            return
        
        print(f"\n{'='*60}")
        print(f"해당 장비(서버)에서 발견된 취약점 [{vuln_name}]은(는) ISMS-P 기준에서")
        print()
        
        for idx, violation in enumerate(result['violations'], 1):
            print(f"{idx}. {violation['분류']} - {violation['항목']}")
        
        print()
        print("이(가) 위반되었습니다.")
        print("="*60)


def main():
    """메인 실행 함수"""
    # 커맨드라인 인자 파서 설정
    parser = argparse.ArgumentParser(
        description="Pentera PDF 보고서에서 Achievements 항목을 추출하고 ISMS-P와 매핑합니다.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  python pentera_ISMS_P.py -R DetailedReport-209_test.pdf
  python pentera_ISMS_P.py --report report.pdf
        """
    )
    
    parser.add_argument(
        '-R', '--report',
        type=str,
        default="DetailedReport-209_test.pdf",
        help='처리할 PDF 보고서 파일 경로 (기본값: DetailedReport-209_test.pdf)'
    )
    
    parser.add_argument(
        '-V', '--vulnerabilities',
        type=str,
        default="pentera_Vulnerabilities.csv",
        help='Pentera 취약점 매핑 CSV 파일 (기본값: pentera_Vulnerabilities.csv)'
    )
    
    parser.add_argument(
        '-I', '--isms',
        type=str,
        default="ISMS_P.csv",
        help='ISMS-P 기준 CSV 파일 (기본값: ISMS_P.csv)'
    )
    
    # 인자 파싱
    args = parser.parse_args()
    
    try:
        # 1. PDF에서 취약점 추출
        print("\n" + "="*60)
        print("Step 1: PDF 보고서에서 취약점 추출")
        print("="*60)
        
        extractor = PenteraPDFExtractor(args.report)
        vulnerabilities = extractor.process()
        
        if not vulnerabilities:
            print("\n취약점을 찾을 수 없습니다.")
            return
        
        # 2. ISMS-P 매핑 데이터 로드
        print("\n" + "="*60)
        print("Step 2: ISMS-P 매핑 데이터 로드")
        print("="*60)
        
        mapper = ISMSPMapper(args.vulnerabilities, args.isms)
        
        # 3. 각 취약점에 대해 ISMS-P 위반 항목 출력
        print("\n" + "="*60)
        print("Step 3: ISMS-P 위반 항목 분석")
        print("="*60)
        
        for vuln in vulnerabilities:
            mapper.print_violation_report(vuln['name'])
        
        # 4. 요약 정보 출력
        print("\n" + "="*60)
        print("=== 요약 ===")
        print("="*60)
        print(f"총 {len(vulnerabilities)}개 취약점 발견")
        
        mapped_count = 0
        for vuln in vulnerabilities:
            if mapper.get_isms_violations(vuln['name']):
                mapped_count += 1
        
        print(f"ISMS-P 매핑 완료: {mapped_count}개")
        print(f"매핑 실패: {len(vulnerabilities) - mapped_count}개")
        print("="*60)
            
    except FileNotFoundError as e:
        print(f"오류: {e}")
    except Exception as e:
        print(f"예상치 못한 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
