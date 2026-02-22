// 전역 변수
let selectedTool = 'pentera';
let selectedFile = null;

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', () => {
    checkLoginStatus();
    initializeToolSelection();
    initializeFileUpload();
});

// 로그인 상태 확인
function checkLoginStatus() {
    const isLoggedIn = localStorage.getItem('isLoggedIn') === 'true';
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    const loginBtn = document.querySelector('.login-btn');
    
    if (isLoggedIn && user.name) {
        // 로그인 상태: 버튼을 사용자명으로 변경
        loginBtn.textContent = `${user.name}님`;
        loginBtn.onclick = toggleUserMenu;
        
        // 플랜 정보 로드
        loadUserPlan(user.id);
    } else {
        // 비로그인 상태
        loginBtn.textContent = '로그인';
        loginBtn.onclick = goToLogin;
        
        // 플랜 배지 숨기기
        const planBadge = document.getElementById('planBadge');
        if (planBadge) planBadge.style.display = 'none';
    }
}

// 사용자 플랜 정보 로드
async function loadUserPlan(userId) {
    console.log('loadUserPlan 호출:', userId);
    try {
        const response = await fetch(`/api/user/profile/${userId}`);
        console.log('API 응답:', response.status);
        if (!response.ok) return;
        
        const data = await response.json();
        console.log('플랜 데이터:', data);
        const planBadge = document.getElementById('planBadge');
        const planName = document.getElementById('planName');
        
        console.log('planBadge element:', planBadge);
        console.log('planName element:', planName);
        
        if (!planBadge || !planName) {
            console.error('플랜 배지 요소를 찾을 수 없습니다');
            return;
        }
        
        const planNames = {
            'free': '무료 플랜',
            'sentinel': 'Sentinel One +',
            'pentera': 'Pentera +',
            'premium': 'Premium +'
        };
        
        planName.textContent = planNames[data.plan] || '무료 플랜';
        planBadge.style.display = 'flex';
        console.log('플랜 배지 표시:', planNames[data.plan]);
        
        // 플랜 배지 클릭 시 마이페이지로 이동
        planBadge.onclick = () => {
            window.location.href = '/mypage#pricing';
        };
    } catch (error) {
        console.error('플랜 정보 로드 실패:', error);
    }
}

// 사용자 메뉴 토글
function toggleUserMenu(event) {
    event.stopPropagation();
    const dropdown = document.getElementById('userDropdown');
    dropdown.classList.toggle('show');
}

// 외부 클릭 시 메뉴 닫기
document.addEventListener('click', (event) => {
    const dropdown = document.getElementById('userDropdown');
    const loginBtn = document.querySelector('.login-btn');
    
    if (dropdown && !dropdown.contains(event.target) && event.target !== loginBtn) {
        dropdown.classList.remove('show');
    }
});

// 로그아웃 모달 표시
function showLogoutModal(event) {
    if (event) event.preventDefault();
    document.getElementById('logoutModal').style.display = 'flex';
    document.getElementById('userDropdown').classList.remove('show');
}

// 로그아웃 모달 닫기
function closeLogoutModal() {
    document.getElementById('logoutModal').style.display = 'none';
}

// 로그아웃 실행
function performLogout() {
    localStorage.removeItem('isLoggedIn');
    localStorage.removeItem('user');
    window.location.href = '/';
}

// 사용자 메뉴 표시 (간단한 로그아웃 구현) - 제거됨

// 도구 선택 초기화
function initializeToolSelection() {
    const toolCards = document.querySelectorAll('.tool-card');
    
    toolCards.forEach(card => {
        card.addEventListener('click', () => {
            const tool = card.dataset.tool;
            
            // 모든 카드 비활성화
            toolCards.forEach(c => {
                c.classList.remove('active');
                const badge = c.querySelector('.status-badge');
                badge.classList.remove('active');
                badge.textContent = '';
            });
            
            // 선택된 카드 활성화
            card.classList.add('active');
            const badge = card.querySelector('.status-badge');
            badge.classList.add('active');
            badge.textContent = '선택됨';
            
            selectedTool = tool;
            
            // 업로드 도움말 텍스트 업데이트
            updateUploadHelpText();
        });
    });
}

// 업로드 도움말 텍스트 업데이트
function updateUploadHelpText() {
    const helpText = document.getElementById('uploadHelpText');
    if (helpText) {
        if (selectedTool === 'sentinelone') {
            helpText.textContent = 'PDF 또는 CSV 파일을 지원합니다';
        } else {
            helpText.textContent = 'PDF 파일만 지원됩니다';
        }
    }
}

// 파일 업로드 초기화
function initializeFileUpload() {
    const uploadArea = document.getElementById('uploadArea');
    const fileInput = document.getElementById('fileInput');
    
    // 드래그 앤 드롭
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });
    
    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('dragover');
    });
    
    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFileSelect(files[0]);
        }
    });
    
    // 파일 선택
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFileSelect(e.target.files[0]);
        }
    });
}

// 파일 선택 처리
function handleFileSelect(file) {
    const isPentera = selectedTool === 'pentera';
    const isSentinelOne = selectedTool === 'sentinelone';
    
    // 파일 타입 검증
    if (isPentera && !file.name.endsWith('.pdf')) {
        alert('Pentera는 PDF 파일만 업로드 가능합니다.');
        return;
    }
    
    if (isSentinelOne && !(file.name.endsWith('.pdf') || file.name.endsWith('.csv'))) {
        alert('SentinelOne은 PDF 또는 CSV 파일만 업로드 가능합니다.');
        return;
    }
    
    if (!isPentera && !isSentinelOne) {
        alert('먼저 분석 도구를 선택해주세요.');
        return;
    }
    
    selectedFile = file;
    
    // UI 업데이트
    document.getElementById('uploadArea').style.display = 'none';
    document.getElementById('selectedFile').style.display = 'flex';
    document.getElementById('analyzeBtn').style.display = 'block';
    
    document.getElementById('fileName').textContent = file.name;
    document.getElementById('fileSize').textContent = formatFileSize(file.size);
}

// 파일 제거
function removeFile() {
    selectedFile = null;
    
    document.getElementById('uploadArea').style.display = 'block';
    document.getElementById('selectedFile').style.display = 'none';
    document.getElementById('analyzeBtn').style.display = 'none';
    document.getElementById('fileInput').value = '';
    
    // 결과 숨기기
    document.getElementById('resultsSection').style.display = 'none';
}

// 대시보드 초기화 (헤더 클릭 시)
function resetDashboard() {
    // 파일 선택 초기화
    selectedFile = null;
    document.getElementById('fileInput').value = '';
    
    // UI 상태 초기화
    document.getElementById('uploadArea').style.display = 'block';
    document.getElementById('selectedFile').style.display = 'none';
    document.getElementById('analyzeBtn').style.display = 'none';
    document.getElementById('resultsSection').style.display = 'none';
    
    // 도구 선택 초기화 (Pentera 기본 선택)
    const toolCards = document.querySelectorAll('.tool-card');
    toolCards.forEach(card => {
        const tool = card.dataset.tool;
        const badge = card.querySelector('.status-badge');
        
        if (tool === 'pentera') {
            card.classList.add('active');
            badge.classList.add('active');
            badge.textContent = '선택됨';
        } else {
            card.classList.remove('active');
            badge.classList.remove('active');
            badge.textContent = '';
        }
    });
    
    selectedTool = 'pentera';
    
    // 상단으로 스크롤
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// 파일 크기 포맷
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

// 보고서 분석
async function analyzeReport() {
    if (!selectedFile) {
        alert('파일을 선택해주세요.');
        return;
    }
    
    // 로그인 체크
    const isLoggedIn = localStorage.getItem('isLoggedIn') === 'true';
    
    if (!isLoggedIn) {
        showLoginModal();
        return;
    }
    
    // 플랜 및 사용 횟수 체크
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    if (user.id) {
        try {
            // 사용 내역 가져오기 (타입별 집계)
            const usageResponse = await fetch(`/api/scan/usage-history/${user.id}`);
            if (usageResponse.ok) {
                const usageData = await usageResponse.json();
                
                // 프로필 정보 가져오기
                const profileResponse = await fetch(`/api/user/profile/${user.id}`);
                const profileData = await profileResponse.json();
                const currentPlan = profileData.plan || 'free';
                
                // 타입별 검사 횟수 집계
                let sentinelCount = 0;
                let penteraCount = 0;
                
                if (usageData.scans && usageData.scans.length > 0) {
                    usageData.scans.forEach(scan => {
                        if (scan.scan_type === 'sentinelone') {
                            sentinelCount++;
                        } else if (scan.scan_type === 'pentera' || !scan.scan_type) {
                            penteraCount++;
                        }
                    });
                }
                
                // 플랜별 한도 설정
                const planLimits = {
                    'free': { sentinel: 10, pentera: 1 },
                    'sentinel': { sentinel: Infinity, pentera: 2 },
                    'pentera': { sentinel: 20, pentera: Infinity },
                    'premium': { sentinel: Infinity, pentera: Infinity }
                };
                
                const limits = planLimits[currentPlan] || planLimits['free'];
                
                // 현재 검사 타입 확인
                const currentScanType = selectedTool === 'sentinelone' ? 'sentinel' : 'pentera';
                const currentCount = currentScanType === 'sentinel' ? sentinelCount : penteraCount;
                const currentLimit = limits[currentScanType];
                
                // 한도 초과 체크
                if (currentCount >= currentLimit) {
                    showUpgradeModal();
                    return;
                }
            }
        } catch (error) {
            console.error('플랜 확인 오류:', error);
        }
    }
    
    // UI 업데이트
    document.getElementById('loadingContainer').style.display = 'block';
    document.getElementById('resultsSection').style.display = 'none';
    document.getElementById('analyzeBtn').disabled = true;
    
    // FormData 생성
    const formData = new FormData();
    formData.append('file', selectedFile);
    
    try {
        // API 호출
        const endpoint = selectedTool === 'pentera' 
            ? '/api/analyze/pentera' 
            : '/api/analyze/sentinelone';
        
        const response = await fetch(endpoint, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error(`서버 오류: ${response.status}`);
        }
        
        const result = await response.json();
        
        // 결과 표시
        displayResults(result);
        
        // 검사 이력 저장
        const user = JSON.parse(localStorage.getItem('user') || '{}');
        if (user.id) {
            await saveScanHistory(user.id, result);
        }
        
    } catch (error) {
        console.error('분석 오류:', error);
        alert(`분석 중 오류가 발생했습니다: ${error.message}`);
    } finally {
        document.getElementById('loadingContainer').style.display = 'none';
        document.getElementById('analyzeBtn').disabled = false;
    }
}

// 결과 표시
function displayResults(result) {
    // SentinelOne 결과 처리
    if (result.threats) {
        displaySentinelOneResults(result);
        return;
    }
    
    // Pentera 결과 처리
    if (!result.vulnerabilities || result.vulnerabilities.length === 0) {
        alert(result.message || '취약점을 찾을 수 없습니다.');
        return;
    }
    
    // 요약 업데이트
    document.getElementById('totalCount').textContent = result.total;
    document.getElementById('mappedCount').textContent = result.mapped;
    document.getElementById('unmappedCount').textContent = result.unmapped;
    
    // 파일 정보 업데이트
    const fileNameEl = document.getElementById('resultFileName');
    const fileSizeEl = document.getElementById('resultFileSize');
    if (fileNameEl && result.filename) {
        fileNameEl.textContent = result.filename;
    }
    if (fileSizeEl && selectedFile) {
        fileSizeEl.textContent = formatFileSize(selectedFile.size);
    }
    
    // 취약점 목록 생성
    const listContainer = document.getElementById('vulnerabilitiesList');
    listContainer.innerHTML = '';
    
    result.vulnerabilities.forEach(vuln => {
        const item = createVulnerabilityItem(vuln);
        listContainer.appendChild(item);
    });
    
    // 파일 업로드 UI 초기화 (다시 분석하지 못하도록)
    selectedFile = null;
    document.getElementById('fileInput').value = '';
    document.getElementById('uploadArea').style.display = 'block';
    document.getElementById('selectedFile').style.display = 'none';
    document.getElementById('analyzeBtn').style.display = 'none';
    
    // 결과 섹션 표시
    document.getElementById('resultsSection').style.display = 'block';
    
    // 스크롤
    document.getElementById('resultsSection').scrollIntoView({ behavior: 'smooth' });
}

// 취약점 아이템 생성
function createVulnerabilityItem(vuln) {
    const div = document.createElement('div');
    div.className = 'vulnerability-item';
    
    const mappedBadge = vuln.mapped 
        ? '<span class="badge badge-mapped">매핑 완료</span>'
        : '<span class="badge badge-unmapped">매핑 실패</span>';
    
    let violationsHTML = '';
    if (vuln.isms_violations && vuln.isms_violations.length > 0) {
        violationsHTML = `
            <div class="isms-violations">
                <h4>ISMS-P 위반 항목</h4>
                ${vuln.isms_violations.map((v, idx) => `
                    <div class="violation-item">
                        <strong>${idx + 1}. ${v.category} - ${v.item}</strong>
                        <p>${v.details || v.criteria}</p>
                    </div>
                `).join('')}
            </div>
        `;
    }
    
    div.innerHTML = `
        <div class="vuln-header">
            <div class="vuln-title">
                <h3>${vuln.vulnerability}</h3>
            </div>
            <div class="vuln-badges">
                <span class="badge badge-severity">심각도: ${vuln.severity}</span>
                <span class="badge badge-number">${vuln.number}</span>
                ${mappedBadge}
            </div>
        </div>
        ${violationsHTML}
    `;
    
    return div;
}

// SentinelOne 결과 표시
function displaySentinelOneResults(result) {
    if (result.total === 0) {
        alert(result.message || '위협이 탐지되지 않았습니다.');
        return;
    }
    
    // 요약 업데이트
    document.getElementById('totalCount').textContent = result.total;
    document.getElementById('mappedCount').textContent = result.mitigated;
    document.getElementById('unmappedCount').textContent = result.active;
    
    // 파일 정보 업데이트
    const fileNameEl = document.getElementById('resultFileName');
    const fileSizeEl = document.getElementById('resultFileSize');
    if (fileNameEl && result.filename) {
        fileNameEl.textContent = result.filename;
    }
    if (fileSizeEl && selectedFile) {
        fileSizeEl.textContent = formatFileSize(selectedFile.size);
    }
    
    // 위협 목록 생성
    const listContainer = document.getElementById('vulnerabilitiesList');
    listContainer.innerHTML = '';
    
    // 보고서 정보 표시
    if (result.report_type && result.report_target) {
        const reportInfo = document.createElement('div');
        reportInfo.className = 'report-info';
        reportInfo.style.cssText = 'background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 12px; padding: 1.5rem; margin-bottom: 2rem;';
        reportInfo.innerHTML = `
            <h3 style="margin: 0 0 1rem 0; color: var(--text-primary); font-size: 1.1rem;">
                📊 보고서 정보
            </h3>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem;">
                <div>
                    <p style="margin: 0; color: var(--text-secondary); font-size: 0.85rem;">유형</p>
                    <p style="margin: 0.25rem 0 0 0; color: var(--text-primary); font-weight: 600;">${result.report_type}</p>
                </div>
                <div>
                    <p style="margin: 0; color: var(--text-secondary); font-size: 0.85rem;">대상</p>
                    <p style="margin: 0.25rem 0 0 0; color: var(--text-primary); font-weight: 600;">${result.report_target}</p>
                </div>
                <div>
                    <p style="margin: 0; color: var(--text-secondary); font-size: 0.85rem;">조치율</p>
                    <p style="margin: 0.25rem 0 0 0; color: ${result.mitigation_rate >= 80 ? 'var(--success-color)' : result.mitigation_rate >= 50 ? 'var(--warning-color)' : 'var(--danger-color)'}; font-weight: 600;">${result.mitigation_rate}%</p>
                </div>
            </div>
        `;
        listContainer.appendChild(reportInfo);
    }
    
    // ISMS-P 제어 항목 표시
    if (result.controls && result.controls.length > 0) {
        const controlsSection = document.createElement('div');
        controlsSection.className = 'controls-section';
        controlsSection.style.cssText = 'margin-bottom: 2rem;';
        
        let controlsHTML = `
            <h3 style="margin: 0 0 1.5rem 0; color: var(--text-primary); font-size: 1.25rem;">
                🔒 ISMS-P 준수 항목 (${result.controls.length}개)
            </h3>
        `;
        
        result.controls.forEach(control => {
            const statusColor = control.status === '적합' ? 'var(--success-color)' : 
                               control.status === '부분 적합' ? 'var(--warning-color)' : 'var(--danger-color)';
            
            controlsHTML += `
                <div class="vulnerability-item" style="margin-bottom: 1rem;">
                    <div class="vuln-header">
                        <div class="vuln-title">
                            <h4 style="margin: 0; color: var(--text-primary); font-size: 1rem;">
                                ${control.code} ${control.title}
                            </h4>
                            <p style="margin: 0.5rem 0 0 0; color: var(--text-secondary); font-size: 0.9rem;">
                                조치: ${control.action}
                            </p>
                        </div>
                        <div class="vuln-badges">
                            <span class="badge" style="background: ${statusColor}20; color: ${statusColor};">
                                ${control.status}
                            </span>
                            <span class="badge badge-number">
                                ${control.mitigated}/${control.total} 조치 완료
                            </span>
                        </div>
                    </div>
                    <div style="margin-top: 1rem; padding-top: 1rem; border-top: 1px solid var(--border-color);">
                        <div style="display: flex; gap: 1rem; flex-wrap: wrap;">
                            <div>
                                <span style="color: var(--text-secondary); font-size: 0.85rem;">총 탐지:</span>
                                <span style="color: var(--text-primary); font-weight: 600; margin-left: 0.25rem;">${control.total}건</span>
                            </div>
                            <div>
                                <span style="color: var(--text-secondary); font-size: 0.85rem;">조치 완료:</span>
                                <span style="color: var(--success-color); font-weight: 600; margin-left: 0.25rem;">${control.mitigated}건</span>
                            </div>
                            <div>
                                <span style="color: var(--text-secondary); font-size: 0.85rem;">조치 필요:</span>
                                <span style="color: var(--danger-color); font-weight: 600; margin-left: 0.25rem;">${control.active}건</span>
                            </div>
                            <div>
                                <span style="color: var(--text-secondary); font-size: 0.85rem;">조치율:</span>
                                <span style="color: ${statusColor}; font-weight: 600; margin-left: 0.25rem;">${control.mitigation_rate}%</span>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        });
        
        controlsSection.innerHTML = controlsHTML;
        listContainer.appendChild(controlsSection);
    }
    
    // 위협 상세 목록 표시
    if (result.threats && result.threats.length > 0) {
        const threatsSection = document.createElement('div');
        threatsSection.innerHTML = `
            <h3 style="margin: 2rem 0 1.5rem 0; color: var(--text-primary); font-size: 1.25rem;">
                ⚠️ 위협 상세 내역 (${result.threats.length}건)
            </h3>
        `;
        listContainer.appendChild(threatsSection);
        
        result.threats.forEach((threat, index) => {
            const threatItem = createSentinelOneThreatItem(threat, index + 1);
            listContainer.appendChild(threatItem);
        });
    }
    
    // 파일 업로드 UI 초기화
    selectedFile = null;
    document.getElementById('fileInput').value = '';
    document.getElementById('uploadArea').style.display = 'block';
    document.getElementById('selectedFile').style.display = 'none';
    document.getElementById('analyzeBtn').style.display = 'none';
    
    // 결과 섹션 표시
    document.getElementById('resultsSection').style.display = 'block';
    
    // 스크롤
    document.getElementById('resultsSection').scrollIntoView({ behavior: 'smooth' });
}

// SentinelOne 위협 아이템 생성
function createSentinelOneThreatItem(threat, index) {
    const div = document.createElement('div');
    div.className = 'vulnerability-item';
    
    const statusBadge = threat.status === 'Mitigated' 
        ? '<span class="badge badge-mapped">조치 완료</span>'
        : '<span class="badge badge-unmapped">조치 필요</span>';
    
    const mappedBadge = threat.mapped 
        ? '<span class="badge" style="background: var(--success-color)20; color: var(--success-color);">매핑 완료</span>'
        : '<span class="badge" style="background: var(--text-secondary)20; color: var(--text-secondary);">매핑 안됨</span>';
    
    let controlsHTML = '';
    if (threat.isms_controls && threat.isms_controls.length > 0) {
        controlsHTML = `
            <div class="isms-violations">
                <h4>ISMS-P 준수 항목</h4>
                ${threat.isms_controls.map((control, idx) => `
                    <div class="violation-item">
                        <strong>${idx + 1}. ${control.code} ${control.title}</strong>
                        <p>${control.action}</p>
                    </div>
                `).join('')}
            </div>
        `;
    }
    
    div.innerHTML = `
        <div class="vuln-header">
            <div class="vuln-title">
                <h3>${index}. ${threat.threat_name}</h3>
                <p style="margin: 0.5rem 0 0 0; color: var(--text-secondary); font-size: 0.9rem;">
                    분류: ${threat.classification.toUpperCase()} | 기기: ${threat.device_name}
                </p>
            </div>
            <div class="vuln-badges">
                <span class="badge" style="background: ${threat.status === 'Mitigated' ? 'var(--success-color)' : 'var(--danger-color)'}20; color: ${threat.status === 'Mitigated' ? 'var(--success-color)' : 'var(--danger-color)'};">
                    ${threat.violation_status}
                </span>
                ${statusBadge}
                ${mappedBadge}
            </div>
        </div>
        ${controlsHTML}
        ${threat.file_hash ? `<p style="margin-top: 1rem; padding-top: 1rem; border-top: 1px solid var(--border-color); color: var(--text-secondary); font-size: 0.85rem;">Hash: ${threat.file_hash}</p>` : ''}
    `;
    
    return div;
}

// 검사 이력 저장
async function saveScanHistory(userId, result) {
    try {
        // SentinelOne 결과인 경우
        if (result.threats) {
            // SentinelOne은 전체 결과 구조를 저장 (controls, report_type 등 포함)
            const sentinelOneData = {
                threats: result.threats,
                controls: result.controls,
                report_type: result.report_type,
                report_target: result.report_target,
                devices: result.devices,
                mitigation_rate: result.mitigation_rate
            };
            
            await fetch('/api/scan/save', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    user_id: userId,
                    filename: result.filename,
                    scan_type: 'sentinelone',
                    total: result.total,
                    mapped: result.mitigated,
                    unmapped: result.active,
                    vulnerabilities: sentinelOneData  // 전체 구조 저장
                })
            });
        } else {
            // Pentera 결과인 경우
            await fetch('/api/scan/save', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    user_id: userId,
                    filename: result.filename,
                    scan_type: 'pentera',
                    total: result.total,
                    mapped: result.mapped,
                    unmapped: result.unmapped,
                    vulnerabilities: result.vulnerabilities
                })
            });
        }
    } catch (error) {
        console.error('검사 이력 저장 오류:', error);
    }
}

// 로그인 모달 표시
function showLoginModal() {
    document.getElementById('loginModal').style.display = 'flex';
}

// 로그인 모달 닫기
function closeLoginModal() {
    document.getElementById('loginModal').style.display = 'none';
}

// 로그인 페이지로 이동
function goToLogin() {
    window.location.href = '/login';
}

// 업그레이드 모달 표시
function showUpgradeModal() {
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    const planNames = {
        'free': '무료 플랜',
        'sentinel': 'Sentinel One +',
        'pentera': 'Pentera +',
        'premium': 'Premium +'
    };
    const currentPlanName = planNames[user.plan] || '무료 플랜';
    
    const planNameEl = document.getElementById('upgradePlanName');
    if (planNameEl) {
        planNameEl.textContent = currentPlanName;
    }
    
    document.getElementById('upgradeModal').style.display = 'flex';
}

// 업그레이드 모달 닫기
function closeUpgradeModal() {
    document.getElementById('upgradeModal').style.display = 'none';
}

// 플랜 업그레이드 페이지로 이동
function goToUpgrade() {
    window.location.href = '/mypage#pricing';
}
