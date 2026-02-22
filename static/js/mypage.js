// 페이지 로드 시 사용자 정보 로드
document.addEventListener('DOMContentLoaded', () => {
    loadUserProfile();
    updateUserMenu();
    loadScanHistory();
    
    // URL 해시가 있으면 해당 섹션으로 이동
    const hash = window.location.hash;
    if (hash) {
        const sectionName = hash.substring(1); // # 제거
        showSection(sectionName);
    }
    
    // 해시 변경 감지
    window.addEventListener('hashchange', () => {
        const hash = window.location.hash;
        if (hash) {
            const sectionName = hash.substring(1);
            showSection(sectionName);
        }
    });
});

// 섹션 네비게이션 헬퍼 함수
function navigateToSection(event, sectionName) {
    if (event) event.preventDefault();
    window.location.hash = sectionName;
    showSection(sectionName);
}

// 사용자 정보 로드
async function loadUserProfile() {
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    console.log('loadUserProfile - user:', user);
    
    if (!user.id) {
        // 로그인하지 않은 경우
        console.log('User ID not found, redirecting to login');
        window.location.href = '/login';
        return;
    }
    
    // 관리자 계정 확인 - username이 'admin'인 경우 관리자 페이지 버튼 표시
    if (user.username === 'admin') {
        const adminMenuItem = document.getElementById('adminPageMenuItem');
        if (adminMenuItem) {
            adminMenuItem.style.display = 'block';
        }
    }
    
    // 기본 정보 표시
    const userNameEl = document.getElementById('userName');
    const userUsernameEl = document.getElementById('userUsername');
    
    if (userNameEl) userNameEl.textContent = user.name || '-';
    if (userUsernameEl) userUsernameEl.textContent = user.username || '-';
    
    // 상세 정보 API 호출
    try {
        console.log(`Fetching user profile from /api/user/profile/${user.id}`);
        const response = await fetch(`/api/user/profile/${user.id}`);
        const data = await response.json();
        console.log('Profile API response:', data);
        
        if (response.ok) {
            const userEmailEl = document.getElementById('userEmail');
            const userPhoneEl = document.getElementById('userPhone');
            const accountCreatedAtEl = document.getElementById('accountCreatedAt');
            const userPlanEl = document.getElementById('userPlan');
            const userPlanUsageEl = document.getElementById('userPlanUsage');
            
            if (userEmailEl) userEmailEl.textContent = data.email || '-';
            if (userPhoneEl) userPhoneEl.textContent = data.phone || '-';
            
            // 플랜 정보 표시
            if (userPlanEl && data.plan) {
                const planNames = {
                    'free': '무료 플랜',
                    'sentinel': 'Sentinel One +',
                    'pentera': 'Pentera +',
                    'premium': 'Premium +'
                };
                userPlanEl.textContent = planNames[data.plan] || data.plan;
                
                // 사용 내역은 검사 통계에서 업데이트됨 (updateScanStats 함수에서 처리)
            }
            
            // 가입일 표시
            if (accountCreatedAtEl && data.created_at) {
                const createdDate = new Date(data.created_at);
                accountCreatedAtEl.textContent = createdDate.toLocaleDateString('ko-KR');
            }
            
            // 요금제 관리 섹션에 현재 플랜 표시
            if (data.plan) {
                highlightCurrentPlan(data.plan);
            }
            
            // 통계 업데이트 - 검사 이력 조회
            await updateScanStats(user.id);
        } else {
            console.error('Profile API error:', data);
        }
    } catch (error) {
        console.error('사용자 정보 로드 오류:', error);
    }
}

// 현재 플랜 강조 표시
function highlightCurrentPlan(currentPlan) {
    const planNames = {
        'free': '무료 플랜',
        'sentinel': 'Sentinel One +',
        'pentera': 'Pentera +',
        'premium': 'Premium +'
    };
    
    // 현재 플랜 정보 박스 업데이트
    const currentPlanInfo = document.getElementById('currentPlanInfo');
    const currentPlanName = document.getElementById('currentPlanName');
    const nextPaymentDate = document.getElementById('nextPaymentDate');
    
    if (currentPlanInfo && currentPlanName) {
        currentPlanName.textContent = planNames[currentPlan] || currentPlan;
        
        // 다음 결제 예정일 계산 (오늘로부터 1개월 후)
        if (nextPaymentDate) {
            const today = new Date();
            const nextMonth = new Date(today);
            nextMonth.setMonth(today.getMonth() + 1);
            
            const year = nextMonth.getFullYear();
            const month = String(nextMonth.getMonth() + 1).padStart(2, '0');
            const day = String(nextMonth.getDate()).padStart(2, '0');
            
            nextPaymentDate.textContent = `${year}.${month}.${day}`;
        }
        
        currentPlanInfo.style.display = 'block';
    }
    
    // 현재 플랜 카드 강조 (테두리 색상 변경)
    document.querySelectorAll('.pricing-card').forEach(card => {
        const cardPlan = card.getAttribute('data-plan');
        if (cardPlan === currentPlan) {
            card.style.borderColor = 'var(--primary-color)';
            card.style.borderWidth = '2px';
            card.style.background = 'linear-gradient(135deg, rgba(99,102,241,0.05), rgba(139,92,246,0.05))';
        } else if (cardPlan !== 'premium') {
            card.style.borderColor = 'var(--border-color)';
            card.style.background = 'var(--card-bg)';
        }
    });
}

// 검사 통계 업데이트
async function updateScanStats(userId) {
    console.log('updateScanStats 호출됨, userId:', userId);
    try {
        // 사용자 프로필에서 scan_count 가져오기
        const profileResponse = await fetch(`/api/user/profile/${userId}`);
        const profileData = await profileResponse.json();
        const scanCount = profileData.scan_count || 0;
        
        // 사용 내역 가져오기 (삭제된 것 포함 - 타입별 집계용)
        const usageResponse = await fetch(`/api/scan/usage-history/${userId}`);
        const usageData = await usageResponse.json();
        
        // 검사 이력 가져오기 (삭제되지 않은 것만 - 통계용)
        const response = await fetch(`/api/scan/history/${userId}`);
        const data = await response.json();
        
        console.log('검사 이력 API 응답:', data);
        console.log('사용자 scan_count:', scanCount);
        
        const totalScansEl = document.getElementById('totalScans');
        const totalVulnsEl = document.getElementById('totalVulns');
        const lastScanEl = document.getElementById('lastScan');
        const sentinelUsageEl = document.getElementById('sentinelUsage');
        const penteraUsageEl = document.getElementById('penteraUsage');
        
        // 현재 사용자 정보 가져오기
        const user = JSON.parse(localStorage.getItem('user') || '{}');
        const currentPlan = user.plan || 'free';
        
        // 총 검사 횟수 (scan_count 사용)
        if (totalScansEl) totalScansEl.textContent = scanCount;
        
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
            'sentinel': { sentinel: '무제한', pentera: 2 },
            'pentera': { sentinel: 20, pentera: '무제한' },
            'premium': { sentinel: '무제한', pentera: '무제한' }
        };
        
        const limits = planLimits[currentPlan] || planLimits['free'];
        
        // Sentinel One 사용 내역 업데이트
        if (sentinelUsageEl) {
            if (limits.sentinel === '무제한') {
                sentinelUsageEl.textContent = '무제한';
            } else {
                sentinelUsageEl.textContent = `${sentinelCount} / ${limits.sentinel}`;
            }
        }
        
        // Pentera 사용 내역 업데이트
        if (penteraUsageEl) {
            if (limits.pentera === '무제한') {
                penteraUsageEl.textContent = '무제한';
            } else {
                penteraUsageEl.textContent = `${penteraCount} / ${limits.pentera}`;
            }
        }
        
        if (data.scans && data.scans.length > 0) {
            console.log('검사 이력 개수:', data.scans.length);
            
            // 총 취약점 수 계산
            const totalVulns = data.scans.reduce((sum, scan) => sum + (scan.total || 0), 0);
            if (totalVulnsEl) totalVulnsEl.textContent = totalVulns;
            
            // 마지막 검사 날짜
            const lastScanDate = new Date(data.scans[0].date);
            const now = new Date();
            const diffMs = now - lastScanDate;
            const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
            
            let lastScanText;
            if (diffDays === 0) {
                lastScanText = '오늘';
            } else if (diffDays === 1) {
                lastScanText = '어제';
            } else if (diffDays < 7) {
                lastScanText = `${diffDays}일 전`;
            } else {
                lastScanText = lastScanDate.toLocaleDateString('ko-KR');
            }
            
            if (lastScanEl) lastScanEl.textContent = lastScanText;
        } else {
            console.log('검사 이력 없음');
            if (totalVulnsEl) totalVulnsEl.textContent = '0';
            if (lastScanEl) lastScanEl.textContent = '-';
        }
    } catch (error) {
        console.error('검사 통계 로드 오류:', error);
    }
}

// 사용자 메뉴 업데이트
function updateUserMenu() {
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    const userMenuBtn = document.getElementById('userMenuBtn');
    
    if (user.name) {
        userMenuBtn.textContent = `${user.name}님`;
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
    const userMenuBtn = document.getElementById('userMenuBtn');
    
    if (dropdown && !dropdown.contains(event.target) && event.target !== userMenuBtn) {
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

// 사용 내역 모달 표시
// 전역 변수로 사용 내역 저장
let allUsageHistory = [];

async function showUsageHistoryModal() {
    const modal = document.getElementById('usageHistoryModal');
    if (!modal) return;
    
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    if (!user || !user.id) return;
    
    try {
        // 사용 내역 전용 API 사용 (삭제된 것 포함)
        const response = await fetch(`/api/scan/usage-history/${user.id}`);
        if (!response.ok) throw new Error('사용 내역을 가져오는데 실패했습니다.');
        
        const data = await response.json();
        allUsageHistory = data.scans || [];
        
        // 날짜 필터 초기화
        resetUsageDateFilter();
        
        // 필터링 적용하여 표시
        filterUsageHistory();
        
        modal.style.display = 'flex';
    } catch (error) {
        console.error('사용 내역 로드 실패:', error);
        alert('사용 내역을 가져오는데 실패했습니다.');
    }
}

// 사용 내역 필터 버튼 토글
function toggleUsageFilter(type) {
    const btn = document.getElementById(type === 'pentera' ? 'usageFilterPentera' : 'usageFilterSentinel');
    if (btn) {
        btn.classList.toggle('active');
        filterUsageHistory();
    }
}

// 사용 내역 필터링
function filterUsageHistory() {
    const tbody = document.getElementById('usageHistoryList');
    if (!tbody) return;
    
    // 검색어
    const searchInput = document.getElementById('usageSearchInput');
    const searchTerm = searchInput ? searchInput.value.toLowerCase().trim() : '';
    
    // 필터 버튼 상태
    const filterPentera = document.getElementById('usageFilterPentera');
    const filterSentinel = document.getElementById('usageFilterSentinel');
    const showPentera = filterPentera ? filterPentera.classList.contains('active') : true;
    const showSentinel = filterSentinel ? filterSentinel.classList.contains('active') : true;
    
    // 날짜 필터
    const startDateInput = document.getElementById('usageStartDate');
    const endDateInput = document.getElementById('usageEndDate');
    const startDate = startDateInput && startDateInput.value ? new Date(startDateInput.value) : null;
    const endDate = endDateInput && endDateInput.value ? new Date(endDateInput.value) : null;
    
    // 종료일의 마지막 시간으로 설정 (23:59:59)
    if (endDate) {
        endDate.setHours(23, 59, 59, 999);
    }
    
    // 필터링
    const filteredHistory = allUsageHistory.filter(item => {
        const scanType = item.scan_type || 'pentera';
        
        // 타입 필터
        if (scanType === 'sentinelone' && !showSentinel) return false;
        if ((scanType === 'pentera' || !item.scan_type) && !showPentera) return false;
        
        // 검색 필터
        if (searchTerm && !item.filename.toLowerCase().includes(searchTerm)) return false;
        
        // 날짜 필터
        if (startDate || endDate) {
            const itemDate = new Date(item.date);
            if (startDate && itemDate < startDate) return false;
            if (endDate && itemDate > endDate) return false;
        }
        
        return true;
    });
    
    // 화면 업데이트
    if (filteredHistory.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" style="padding: 2rem; text-align: center; color: var(--text-secondary);">조건에 맞는 내역이 없습니다.</td></tr>';
    } else {
        tbody.innerHTML = filteredHistory.map((item, index) => {
            const date = new Date(item.date);
            const formattedDate = `${date.getFullYear()}.${String(date.getMonth() + 1).padStart(2, '0')}.${String(date.getDate()).padStart(2, '0')} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}:${String(date.getSeconds()).padStart(2, '0')}`;
            const serviceName = item.scan_type === 'sentinelone' ? 'Sentinel One 매칭 시스템 이용' : 'Pentera 매칭 시스템 이용';
            
            return `
                <tr style="border-bottom: 1px solid var(--border-color);" data-scan-type="${item.scan_type || 'pentera'}" data-filename="${item.filename}">
                    <td style="padding: 1rem; text-align: center; color: var(--text-secondary);">${index + 1}</td>
                    <td style="padding: 1rem; color: var(--text-primary);">${formattedDate}</td>
                    <td style="padding: 1rem; color: var(--text-primary);">${item.filename}</td>
                    <td style="padding: 1rem; color: var(--text-primary);">${serviceName}</td>
                </tr>
            `;
        }).join('');
    }
}

// 날짜 필터 초기화 (기본값: 전달 1일 ~ 오늘)
function resetUsageDateFilter() {
    const startDateInput = document.getElementById('usageStartDate');
    const endDateInput = document.getElementById('usageEndDate');
    
    if (startDateInput && endDateInput) {
        const today = new Date();
        const lastMonth = new Date(today.getFullYear(), today.getMonth() - 1, 1);
        
        // YYYY-MM-DD 형식으로 변환
        const formatDate = (date) => {
            const year = date.getFullYear();
            const month = String(date.getMonth() + 1).padStart(2, '0');
            const day = String(date.getDate()).padStart(2, '0');
            return `${year}-${month}-${day}`;
        };
        
        startDateInput.value = formatDate(lastMonth);  // 전달 1일
        endDateInput.value = formatDate(today);        // 오늘
    }
    
    filterUsageHistory();
}

// 사용 내역 모달 닫기
function closeUsageHistoryModal() {
    const modal = document.getElementById('usageHistoryModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

// ==================== 관리자 페이지 ====================

let selectedUserId = null;
let selectedUserName = null;

// 관리자 통계 로드
async function loadAdminStats() {
    try {
        const response = await fetch('/api/admin/stats');
        if (!response.ok) throw new Error('통계 로드 실패');
        
        const data = await response.json();
        
        document.getElementById('totalUsers').textContent = data.total_users;
        document.getElementById('totalScans').textContent = data.total_scans;
        document.getElementById('premiumUsers').textContent = data.premium_users;
    } catch (error) {
        console.error('통계 로드 오류:', error);
    }
}

// 전체 사용자 목록 로드
async function loadAllUsers() {
    try {
        const response = await fetch('/api/admin/users');
        if (!response.ok) throw new Error('사용자 목록 로드 실패');
        
        const data = await response.json();
        const tbody = document.getElementById('usersTableBody');
        
        if (!data.users || data.users.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" style="padding: 2rem; text-align: center; color: var(--text-secondary);">사용자가 없습니다.</td></tr>';
            return;
        }
        
        tbody.innerHTML = data.users.map(user => {
            const date = new Date(user.created_at);
            const formattedDate = `${date.getFullYear()}.${String(date.getMonth() + 1).padStart(2, '0')}.${String(date.getDate()).padStart(2, '0')}`;
            
            return `
                <tr style="border-bottom: 1px solid var(--border-color);">
                    <td style="padding: 1rem; color: var(--text-primary);">${user.id}</td>
                    <td style="padding: 1rem; color: var(--text-primary);">${user.name}</td>
                    <td style="padding: 1rem; color: var(--text-primary);">${user.username}</td>
                    <td style="padding: 1rem; color: var(--text-primary);">${user.email}</td>
                    <td style="padding: 1rem; text-align: center; color: var(--text-primary);">${user.scan_count}</td>
                    <td style="padding: 1rem; text-align: center; color: var(--text-secondary);">${formattedDate}</td>
                    <td style="padding: 1rem; text-align: center;">
                        <button onclick="showUserManageModal(${user.id}, '${user.name}', '${user.plan}')" class="btn-secondary" style="padding: 0.4rem 0.75rem; font-size: 0.875rem;">사용자 관리</button>
                    </td>
                </tr>
            `;
        }).join('');
    } catch (error) {
        console.error('사용자 목록 로드 오류:', error);
        const tbody = document.getElementById('usersTableBody');
        tbody.innerHTML = '<tr><td colspan="7" style="padding: 2rem; text-align: center; color: #ef4444;">사용자 목록을 불러오는데 실패했습니다.</td></tr>';
    }
}

// 사용자 관리 모달 표시
function showUserManageModal(userId, userName, currentPlan) {
    selectedUserId = userId;
    selectedUserName = userName;
    
    const planNames = {
        'free': '무료 플랜',
        'sentinel': 'Sentinel One +',
        'pentera': 'Pentera +',
        'premium': 'Premium +'
    };
    
    document.getElementById('manageUserName').textContent = userName;
    document.getElementById('manageCurrentPlan').textContent = planNames[currentPlan] || currentPlan;
    document.getElementById('managePlanSelect').value = currentPlan;
    document.getElementById('userManageModal').style.display = 'flex';
}

// 사용자 관리 모달 닫기
function closeUserManageModal() {
    document.getElementById('userManageModal').style.display = 'none';
    selectedUserId = null;
    selectedUserName = null;
}

// 플랜 변경 실행
async function performChangePlan() {
    if (!selectedUserId) return;
    
    const newPlan = document.getElementById('managePlanSelect').value;
    
    try {
        const response = await fetch(`/api/admin/user/${selectedUserId}/plan`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ plan: newPlan })
        });
        
        if (response.ok) {
            alert('플랜이 변경되었습니다.');
            closeUserManageModal();
            loadAllUsers(); // 목록 새로고침
        } else {
            alert('플랜 변경에 실패했습니다.');
        }
    } catch (error) {
        console.error('플랜 변경 오류:', error);
        alert('플랜 변경 중 오류가 발생했습니다.');
    }
}

// 모달에서 사용자 삭제
async function deleteUserFromModal() {
    if (!selectedUserId || !selectedUserName) return;
    
    if (!confirm(`정말로 "${selectedUserName}" 사용자를 삭제하시겠습니까?\n이 작업은 되돌릴 수 없습니다.`)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/admin/user/${selectedUserId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            alert('사용자가 삭제되었습니다.');
            closeUserManageModal();
            loadAllUsers(); // 목록 새로고침
            loadAdminStats(); // 통계 새로고침
        } else {
            alert('사용자 삭제에 실패했습니다.');
        }
    } catch (error) {
        console.error('사용자 삭제 오류:', error);
        alert('사용자 삭제 중 오류가 발생했습니다.');
    }
}

// 검사 내역 초기화
async function clearUserScanHistory() {
    if (!selectedUserId || !selectedUserName) return;
    
    if (!confirm(`"${selectedUserName}" 사용자의 모든 검사 내역을 삭제하시겠습니까?\n이 작업은 되돌릴 수 없습니다.`)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/admin/user/${selectedUserId}/clear-scans`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            alert('검사 내역이 초기화되었습니다.');
            loadAllUsers(); // 목록 새로고침 (검사 수 업데이트)
            loadAdminStats(); // 통계 새로고침
            
            // 현재 로그인한 사용자 본인의 검사 내역을 초기화한 경우
            const currentUser = JSON.parse(localStorage.getItem('user') || '{}');
            if (currentUser.id === selectedUserId) {
                // 프로필 정보 다시 로드하여 총 검사 횟수 업데이트
                await loadUserProfile();
                // 검사 이력도 다시 로드
                await loadScanHistory();
                // 사용 통계도 업데이트
                await updateScanStats();
            }
        } else {
            const data = await response.json();
            alert(data.detail || '검사 내역 초기화에 실패했습니다.');
        }
    } catch (error) {
        console.error('검사 내역 초기화 오류:', error);
        alert('검사 내역 초기화 중 오류가 발생했습니다.');
    }
}

// 사용자 삭제 (기존 함수 - 호환성 유지)
async function deleteUserByAdmin(userId, userName) {
    if (!confirm(`정말로 "${userName}" 사용자를 삭제하시겠습니까?\n이 작업은 되돌릴 수 없습니다.`)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/admin/user/${userId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            alert('사용자가 삭제되었습니다.');
            loadAllUsers(); // 목록 새로고침
            loadAdminStats(); // 통계 새로고침
        } else {
            alert('사용자 삭제에 실패했습니다.');
        }
    } catch (error) {
        console.error('사용자 삭제 오류:', error);
        alert('사용자 삭제 중 오류가 발생했습니다.');
    }
}

// 섹션 전환
function showSection(sectionName, event) {
    // 모든 섹션 숨기기
    document.querySelectorAll('.content-section').forEach(section => {
        section.style.display = 'none';
    });
    
    // 모든 메뉴 링크 비활성화
    document.querySelectorAll('.sidebar-menu-link').forEach(link => {
        link.classList.remove('active');
    });
    
    // 선택된 섹션 표시
    const sectionMap = {
        'profile': 'profileSection',
        'pricing': 'pricingSection',
        'history': 'historySection',
        'edit': 'editSection',
        'settings': 'settingsSection',
        'admin': 'adminSection'
    };
    
    const sectionId = sectionMap[sectionName];
    if (sectionId) {
        document.getElementById(sectionId).style.display = 'block';
    }
    
    // 클릭된 메뉴 활성화 (이벤트가 있을 경우에만)
    if (event && event.target) {
        event.target.closest('.sidebar-menu-link').classList.add('active');
    } else {
        // 프로그래밍 방식 호출 시 해당 메뉴 찾아서 활성화
        const menuLinks = document.querySelectorAll('.sidebar-menu-link');
        menuLinks.forEach(link => {
            if (link.getAttribute('onclick')?.includes(sectionName)) {
                link.classList.add('active');
            }
        });
    }
    
    // 관리자 페이지인 경우 데이터 로드
    if (sectionName === 'admin') {
        loadAdminStats();
        loadAllUsers();
    }
    
    // 검사 이력 섹션인 경우 다시 로드
    if (sectionName === 'history') {
        loadScanHistory();
    }
    
    // 개인정보 수정 섹션인 경우 비밀번호 확인
    if (sectionName === 'edit') {
        showPasswordVerifyModal();
    }
}

// 검사 이력 로드
// 전역 변수로 검사 이력 저장
let allScans = [];

async function loadScanHistory() {
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    console.log('loadScanHistory - user:', user);
    
    if (!user.id) {
        console.log('User ID not found in loadScanHistory');
        return;
    }
    
    try {
        console.log(`Fetching scan history from /api/scan/history/${user.id}`);
        const response = await fetch(`/api/scan/history/${user.id}`);
        const data = await response.json();
        console.log('Scan history API response:', data);
        
        // 전역 변수에 저장
        allScans = data.scans || [];
        
        // 날짜 필터 초기화
        resetHistoryDateFilter();
        
        // 필터링 적용하여 표시
        filterScanHistory();
        
    } catch (error) {
        console.error('검사 이력 로드 오류:', error);
    }
}

// 필터 버튼 토글
function toggleFilter(type) {
    const btn = document.getElementById(type === 'pentera' ? 'filterPentera' : 'filterSentinel');
    if (btn) {
        btn.classList.toggle('active');
        filterScanHistory();
    }
}

// 검사 이력 날짜 필터 초기화 (기본값: 전달 1일 ~ 오늘)
function resetHistoryDateFilter() {
    const startDateInput = document.getElementById('historyStartDate');
    const endDateInput = document.getElementById('historyEndDate');
    
    if (startDateInput && endDateInput) {
        const today = new Date();
        const lastMonth = new Date(today.getFullYear(), today.getMonth() - 1, 1);
        
        // YYYY-MM-DD 형식으로 변환
        const formatDate = (date) => {
            const year = date.getFullYear();
            const month = String(date.getMonth() + 1).padStart(2, '0');
            const day = String(date.getDate()).padStart(2, '0');
            return `${year}-${month}-${day}`;
        };
        
        startDateInput.value = formatDate(lastMonth);  // 전달 1일
        endDateInput.value = formatDate(today);        // 오늘
    }
}

// 검사 이력 필터링 및 표시
function filterScanHistory() {
    const historyContainer = document.getElementById('historyContainer');
    if (!historyContainer) {
        console.error('historyContainer element not found');
        return;
    }
    
    // 검색어
    const searchInput = document.getElementById('historySearchInput');
    const searchTerm = searchInput ? searchInput.value.toLowerCase().trim() : '';
    
    // 필터 버튼 상태
    const filterPentera = document.getElementById('filterPentera');
    const filterSentinel = document.getElementById('filterSentinel');
    const showPentera = filterPentera ? filterPentera.classList.contains('active') : true;
    const showSentinel = filterSentinel ? filterSentinel.classList.contains('active') : true;
    
    // 날짜 필터
    const startDateInput = document.getElementById('historyStartDate');
    const endDateInput = document.getElementById('historyEndDate');
    const startDate = startDateInput && startDateInput.value ? new Date(startDateInput.value) : null;
    const endDate = endDateInput && endDateInput.value ? new Date(endDateInput.value) : null;
    
    // 종료일의 마지막 시간으로 설정 (23:59:59)
    if (endDate) {
        endDate.setHours(23, 59, 59, 999);
    }
    
    // 필터링
    const filteredScans = allScans.filter(scan => {
        const scanType = scan.scan_type || 'pentera';
        
        // 타입 필터
        if (scanType === 'sentinelone' && !showSentinel) return false;
        if ((scanType === 'pentera' || !scan.scan_type) && !showPentera) return false;
        
        // 검색 필터
        if (searchTerm && !scan.filename.toLowerCase().includes(searchTerm)) return false;
        
        // 날짜 필터
        if (startDate || endDate) {
            const scanDate = new Date(scan.date);
            if (startDate && scanDate < startDate) return false;
            if (endDate && scanDate > endDate) return false;
        }
        
        return true;
    });
    
    // 화면 업데이트
    if (filteredScans.length > 0) {
        console.log(`Rendering ${filteredScans.length} filtered scan history items`);
        let html = '<div class="scan-history-list">';
        
        filteredScans.forEach(scan => {
            const date = new Date(scan.date).toLocaleString('ko-KR');
            const scanType = scan.scan_type || 'pentera';
            const logoUrl = scanType === 'sentinelone' ? '/static/images/SentinelOne_logo.png' : '/static/images/Pentera_logo.png';
            const scanLabel = scanType === 'sentinelone' ? 'SentinelOne' : 'Pentera';
            
            html += `
                <div class="scan-history-item" onclick="showScanDetail(${scan.id})" data-scan-type="${scanType}" data-filename="${scan.filename}">
                    <img src="${logoUrl}" alt="${scanLabel}" class="scan-type-logo" title="${scanLabel} 검사">
                    <div class="scan-info">
                        <h3 class="scan-filename">${scan.filename}</h3>
                        <p class="scan-date">${date}</p>
                    </div>
                    <div class="scan-stats">
                        <span class="stat-item">
                            <strong>총 ${scan.total}개</strong> 취약점
                        </span>
                        <span class="stat-item success">
                            <strong>${scan.mapped}개</strong> 매핑 완료
                        </span>
                        <span class="stat-item warning">
                            <strong>${scan.unmapped}개</strong> 매핑 실패
                        </span>
                    </div>
                </div>
            `;
        });
        
        html += '</div>';
        historyContainer.innerHTML = html;
    } else {
        console.log('No scans match filter, showing empty message');
        if (allScans.length === 0) {
            historyContainer.innerHTML = '<p style="text-align: center; color: var(--text-secondary); padding: 3rem;">검사 이력이 없습니다.</p>';
        } else {
            historyContainer.innerHTML = '<p style="text-align: center; color: var(--text-secondary); padding: 3rem;">검색 조건에 맞는 검사 이력이 없습니다.</p>';
        }
    }
}

// 검사 상세 정보 표시
async function showScanDetail(scanId) {
    try {
        const response = await fetch(`/api/scan/detail/${scanId}`);
        const data = await response.json();
        
        // 모달 생성
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.style.display = 'flex';
        modal.id = 'scanDetailModal';
        
        // SentinelOne 형식인지 확인 (vulnerabilities가 객체 형태로 threats, controls 포함)
        const isSentinelOne = data.vulnerabilities && typeof data.vulnerabilities === 'object' && data.vulnerabilities.threats;
        
        let contentHTML = '';
        
        if (isSentinelOne) {
            // SentinelOne 형식
            const sentinelData = data.vulnerabilities;
            const threats = sentinelData.threats || [];
            const controls = sentinelData.controls || [];
            
            // ISMS-P 준수 항목 섹션
            let controlsHTML = '';
            if (controls.length > 0) {
                controlsHTML = `
                    <h3 style="margin: 2rem 0 1.5rem 0; color: var(--text-primary); font-size: 1.25rem;">
                        🔒 ISMS-P 준수 항목 (${controls.length}개)
                    </h3>
                `;
                
                controls.forEach(control => {
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
            }
            
            // 위협 상세 내역 섹션
            let threatsHTML = '';
            if (threats.length > 0) {
                threatsHTML = `
                    <h3 style="margin: 2rem 0 1.5rem 0; color: var(--text-primary); font-size: 1.25rem;">
                        ⚠️ 위협 상세 내역 (${threats.length}건)
                    </h3>
                `;
                
                threats.forEach((threat, index) => {
                    const statusBadge = threat.status === 'Mitigated' 
                        ? '<span class="badge badge-mapped">조치 완료</span>'
                        : '<span class="badge badge-unmapped">조치 필요</span>';
                    
                    const mappedBadge = threat.mapped 
                        ? '<span class="badge" style="background: var(--success-color)20; color: var(--success-color);">매핑 완료</span>'
                        : '<span class="badge" style="background: var(--text-secondary)20; color: var(--text-secondary);">매핑 안됨</span>';
                    
                    let controlsListHTML = '';
                    if (threat.isms_controls && threat.isms_controls.length > 0) {
                        controlsListHTML = `
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
                    
                    threatsHTML += `
                        <div class="vulnerability-item" style="margin-bottom: 1rem;">
                            <div class="vuln-header">
                                <div class="vuln-title">
                                    <h3>${index + 1}. ${threat.threat_name}</h3>
                                    <p style="margin: 0.5rem 0 0 0; color: var(--text-secondary); font-size: 0.9rem;">
                                        분류: ${threat.classification.toUpperCase()} | 기기: ${threat.device_name || '-'}
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
                            ${controlsListHTML}
                            ${threat.file_hash ? `<p style="margin-top: 1rem; padding-top: 1rem; border-top: 1px solid var(--border-color); color: var(--text-secondary); font-size: 0.85rem;">Hash: ${threat.file_hash}</p>` : ''}
                        </div>
                    `;
                });
            }
            
            contentHTML = controlsHTML + threatsHTML;
        } else {
            // Pentera 형식 (기존 로직)
            let vulnHTML = '';
            
            if (!data.vulnerabilities || data.vulnerabilities.length === 0) {
                vulnHTML = '<p style="color: var(--text-secondary); text-align: center; padding: 2rem;">취약점 정보가 없습니다.</p>';
            } else {
                data.vulnerabilities.forEach((vuln, index) => {
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
                    
                    vulnHTML += `
                        <div class="vulnerability-item" style="margin-bottom: 1rem;">
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
                        </div>
                    `;
                });
            }
            
            contentHTML = vulnHTML;
        }
        
        const date = new Date(data.date).toLocaleString('ko-KR');
        
        modal.innerHTML = `
            <div class="modal-content" style="max-width: 900px; max-height: 90vh; overflow-y: auto;">
                <div class="modal-header" style="position: relative;">
                    <h2>검사 상세 정보</h2>
                    <button onclick="confirmDeleteScan(${scanId})" class="delete-scan-btn" title="이력 삭제">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2M10 11v6M14 11v6"/>
                        </svg>
                    </button>
                </div>
                <div style="padding: 1rem 0;">
                    <div style="margin-bottom: 1.5rem;">
                        <p style="color: var(--text-secondary); margin-bottom: 0.5rem;">파일명</p>
                        <p style="color: var(--text-primary); font-size: 1.125rem; font-weight: 600;">${data.filename}</p>
                    </div>
                    <div style="margin-bottom: 1.5rem;">
                        <p style="color: var(--text-secondary); margin-bottom: 0.5rem;">검사 일시</p>
                        <p style="color: var(--text-primary);">${date}</p>
                    </div>
                    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; margin-bottom: 2rem;">
                        <div style="background: var(--hover-bg); padding: 1rem; border-radius: 0.5rem; text-align: center;">
                            <p style="color: var(--text-secondary); font-size: 0.875rem;">총 발견된 위협</p>
                            <p style="color: var(--primary-color); font-size: 1.5rem; font-weight: 700;">${data.total}</p>
                        </div>
                        <div style="background: var(--hover-bg); padding: 1rem; border-radius: 0.5rem; text-align: center;">
                            <p style="color: var(--text-secondary); font-size: 0.875rem;">조치 완료</p>
                            <p style="color: #10b981; font-size: 1.5rem; font-weight: 700;">${data.mapped}</p>
                        </div>
                        <div style="background: var(--hover-bg); padding: 1rem; border-radius: 0.5rem; text-align: center;">
                            <p style="color: var(--text-secondary); font-size: 0.875rem;">조치 필요</p>
                            <p style="color: #ef4444; font-size: 1.5rem; font-weight: 700;">${data.unmapped}</p>
                        </div>
                    </div>
                    <div style="max-height: 500px; overflow-y: auto;">
                        ${contentHTML}
                    </div>
                </div>
                <div class="modal-actions">
                    <button class="btn-primary" onclick="closeScanDetailModal()">닫기</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
    } catch (error) {
        console.error('검사 상세 조회 오류:', error);
        alert('검사 상세 정보를 불러오는데 실패했습니다.');
    }
}

// 검사 상세 모달 닫기
function closeScanDetailModal() {
    const modal = document.getElementById('scanDetailModal');
    if (modal) {
        modal.remove();
    }
}

// 검사 이력 삭제 확인
function confirmDeleteScan(scanId) {
    const confirmModal = document.createElement('div');
    confirmModal.className = 'modal';
    confirmModal.style.display = 'flex';
    confirmModal.id = 'deleteConfirmModal';
    
    confirmModal.innerHTML = `
        <div class="modal-content" style="max-width: 400px;">
            <div class="modal-header">
                <h2>검사 이력 삭제</h2>
            </div>
            <div class="modal-text">
                이 검사 이력을 삭제하시겠습니까?<br>
                삭제된 데이터는 복구할 수 없습니다.
            </div>
            <div class="modal-actions">
                <button class="btn-secondary" onclick="closeDeleteConfirmModal()">취소</button>
                <button class="btn-danger" onclick="deleteScanHistory(${scanId})">삭제</button>
            </div>
        </div>
    `;
    
    document.body.appendChild(confirmModal);
}

// 삭제 확인 모달 닫기
function closeDeleteConfirmModal() {
    const modal = document.getElementById('deleteConfirmModal');
    if (modal) {
        modal.remove();
    }
}

// 검사 이력 삭제 실행
async function deleteScanHistory(scanId) {
    try {
        console.log(`Deleting scan history: ${scanId}`);
        const response = await fetch(`/api/scan/delete/${scanId}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        console.log('Delete response:', response.status, data);
        
        if (response.ok) {
            // 성공 시 모든 모달 닫기
            closeDeleteConfirmModal();
            closeScanDetailModal();
            
            console.log('Reloading scan history...');
            // 검사 이력 새로고침
            await loadScanHistory();
            
            // 통계 업데이트
            const user = JSON.parse(localStorage.getItem('user') || '{}');
            if (user.id) {
                await updateScanStats(user.id);
            }
            
            alert('검사 이력이 삭제되었습니다.');
        } else {
            alert(data.detail || '검사 이력 삭제에 실패했습니다.');
        }
    } catch (error) {
        console.error('검사 이력 삭제 오류:', error);
        alert('검사 이력 삭제 중 오류가 발생했습니다.');
    }
}

// ========== 개인정보 수정 기능 ==========

// 비밀번호 확인 모달 표시
function showPasswordVerifyModal() {
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.style.display = 'flex';
    modal.id = 'passwordVerifyModal';
    
    modal.innerHTML = `
        <div class="modal-content" style="max-width: 400px;">
            <div class="modal-header">
                <h2>비밀번호 확인</h2>
            </div>
            <div class="modal-text">
                개인정보를 수정하려면 비밀번호를 입력하세요.
            </div>
            <div class="form-group" style="margin-bottom: 1.5rem;">
                <input type="password" id="verifyPasswordInput" class="form-input" placeholder="비밀번호" onkeypress="if(event.key==='Enter') verifyPassword()">
            </div>
            <div class="modal-actions">
                <button class="btn-secondary" onclick="closePasswordVerifyModal()">취소</button>
                <button class="btn-primary" onclick="verifyPassword()">확인</button>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    setTimeout(() => document.getElementById('verifyPasswordInput').focus(), 100);
}

// 비밀번호 확인 모달 닫기
function closePasswordVerifyModal(returnToProfile = true) {
    const modal = document.getElementById('passwordVerifyModal');
    if (modal) {
        modal.remove();
    }
    // 취소 시에만 프로필 섹션으로 돌아가기
    if (returnToProfile) {
        showSection('profile');
    }
}

// 비밀번호 확인
async function verifyPassword() {
    const password = document.getElementById('verifyPasswordInput').value;
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    
    console.log('Verifying password for user:', user.id);
    
    if (!password) {
        alert('비밀번호를 입력하세요.');
        return;
    }
    
    try {
        console.log('Sending password verification request...');
        const response = await fetch('/api/user/verify-password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: user.id, password })
        });
        
        console.log('Response status:', response.status);
        const data = await response.json();
        console.log('Response data:', data);
        
        if (response.ok) {
            closePasswordVerifyModal(false); // 모달만 닫고 페이지 이동 안 함
            loadEditForm();
        } else {
            alert(data.detail || '비밀번호가 일치하지 않습니다.');
        }
    } catch (error) {
        console.error('비밀번호 확인 오류:', error);
        alert('비밀번호 확인 중 오류가 발생했습니다.');
    }
}

// 수정 폼 로드
async function loadEditForm() {
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    
    // 현재 정보 조회
    try {
        const response = await fetch(`/api/user/profile/${user.id}`);
        const data = await response.json();
        
        if (response.ok) {
            document.getElementById('passwordVerifyMessage').style.display = 'none';
            document.getElementById('editForm').style.display = 'block';
            
            // 폼에 현재 값 설정
            document.getElementById('editName').value = data.name || '';
            document.getElementById('editUsername').value = data.username || '';
            document.getElementById('editPhone').value = data.phone || '';
        }
    } catch (error) {
        console.error('사용자 정보 로드 오류:', error);
    }
}

// 아이디 중복 검사 상태
let isUsernameChecked = false;
let checkedUsername = '';

// 아이디 중복 검사
async function checkUsername() {
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    const username = document.getElementById('editUsername').value.trim();
    const resultEl = document.getElementById('usernameCheckResult');
    
    if (!username) {
        alert('아이디를 입력하세요.');
        return;
    }
    
    try {
        const response = await fetch('/api/user/check-username', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, user_id: user.id })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            if (data.available) {
                resultEl.style.color = '#10b981';
                resultEl.textContent = '✓ 사용 가능한 아이디입니다.';
                isUsernameChecked = true;
                checkedUsername = username;
            } else {
                resultEl.style.color = '#ef4444';
                resultEl.textContent = '✗ 이미 사용 중인 아이디입니다.';
                isUsernameChecked = false;
            }
        }
    } catch (error) {
        console.error('아이디 중복 검사 오류:', error);
        alert('아이디 중복 검사 중 오류가 발생했습니다.');
    }
}

// 아이디 입력 시 중복검사 초기화
function resetUsernameCheck() {
    const username = document.getElementById('editUsername').value.trim();
    if (username !== checkedUsername) {
        isUsernameChecked = false;
        document.getElementById('usernameCheckResult').textContent = '';
    }
}

// 기본 정보 수정
async function updateBasicInfo() {
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    const name = document.getElementById('editName').value.trim();
    const username = document.getElementById('editUsername').value.trim();
    const phone = document.getElementById('editPhone').value.trim();
    
    if (!name || !username || !phone) {
        alert('모든 필드를 입력하세요.');
        return;
    }
    
    // 아이디가 변경되었고 중복검사를 하지 않았다면
    if (username !== user.username && !isUsernameChecked) {
        alert('아이디 중복 확인을 먼저 해주세요.');
        return;
    }
    
    if (username !== user.username && checkedUsername !== username) {
        alert('아이디가 변경되었습니다. 다시 중복 확인을 해주세요.');
        return;
    }
    
    try {
        const response = await fetch('/api/user/update-basic', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: user.id,
                name,
                username,
                phone
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            // localStorage 업데이트
            localStorage.setItem('user', JSON.stringify(data.user));
            alert('정보가 수정되었습니다.');
            loadUserProfile();
            updateUserMenu(); // 헤더의 사용자 이름 업데이트
        } else {
            alert(data.detail || '정보 수정에 실패했습니다.');
        }
    } catch (error) {
        console.error('정보 수정 오류:', error);
        alert('정보 수정 중 오류가 발생했습니다.');
    }
}

// 이메일 인증번호 발송
async function sendEmailVerification() {
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    const newEmail = document.getElementById('newEmail').value.trim();
    
    if (!newEmail) {
        alert('새 이메일을 입력하세요.');
        return;
    }
    
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(newEmail)) {
        alert('올바른 이메일 형식이 아닙니다.');
        return;
    }
    
    try {
        const response = await fetch('/api/user/update-email-verify', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: user.id, email: newEmail })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            document.getElementById('emailVerifyGroup').style.display = 'block';
            alert('인증번호가 발송되었습니다.');
        } else {
            alert(data.detail || '인증번호 발송에 실패했습니다.');
        }
    } catch (error) {
        console.error('인증번호 발송 오류:', error);
        alert('인증번호 발송 중 오류가 발생했습니다.');
    }
}

// 이메일 변경
async function updateEmail() {
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    const newEmail = document.getElementById('newEmail').value.trim();
    const code = document.getElementById('emailVerifyCode').value.trim();
    
    if (!newEmail || !code) {
        alert('이메일과 인증번호를 모두 입력하세요.');
        return;
    }
    
    try {
        const response = await fetch('/api/user/update-email', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: user.id, email: newEmail, code })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            // localStorage 업데이트
            user.email = data.email;
            localStorage.setItem('user', JSON.stringify(user));
            
            alert('이메일이 변경되었습니다.');
            document.getElementById('newEmail').value = '';
            document.getElementById('emailVerifyCode').value = '';
            document.getElementById('emailVerifyGroup').style.display = 'none';
            loadUserProfile();
        } else {
            alert(data.detail || '이메일 변경에 실패했습니다.');
        }
    } catch (error) {
        console.error('이메일 변경 오류:', error);
        alert('이메일 변경 중 오류가 발생했습니다.');
    }
}

// 비밀밀호 강도 검사
function checkPasswordStrength() {
    const password = document.getElementById('newPassword').value;
    const strengthBar = document.getElementById('passwordStrengthFill');
    const strengthText = document.getElementById('passwordStrengthText');
    
    if (!password) {
        strengthBar.style.width = '0';
        strengthText.textContent = '';
        return;
    }
    
    let strength = 0;
    let message = '';
    let color = '';
    
    // 길이 검사
    if (password.length >= 8) strength += 25;
    if (password.length >= 12) strength += 25;
    
    // 대소문자 혼합
    if (/[a-z]/.test(password) && /[A-Z]/.test(password)) strength += 25;
    
    // 숫자 포함
    if (/\d/.test(password)) strength += 12.5;
    
    // 특수문자 포함
    if (/[!@#$%^&*(),.?":{}|<>]/.test(password)) strength += 12.5;
    
    if (strength <= 25) {
        message = '매우 약함';
        color = '#ef4444';
    } else if (strength <= 50) {
        message = '약함';
        color = '#f59e0b';
    } else if (strength <= 75) {
        message = '보통';
        color = '#eab308';
    } else {
        message = '강함';
        color = '#10b981';
    }
    
    strengthBar.style.width = strength + '%';
    strengthBar.style.background = color;
    strengthText.textContent = message;
    strengthText.style.color = color;
}

// 비밀밀호 변경 인증번호 발송
async function sendPasswordVerification() {
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    
    try {
        const response = await fetch('/api/user/update-password-verify', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: user.id })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            document.getElementById('passwordChangeGroup').style.display = 'block';
            alert(`인증번호가 ${data.email}로 발송되었습니다.`);
        } else {
            alert(data.detail || '인증번호 발송에 실패했습니다.');
        }
    } catch (error) {
        console.error('인증번호 발송 오류:', error);
        alert('인증번호 발송 중 오류가 발생했습니다.');
    }
}

// 비밀번호 변경
async function updatePassword() {
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    const code = document.getElementById('passwordVerifyCode').value.trim();
    const newPassword = document.getElementById('newPassword').value;
    const confirmPassword = document.getElementById('newPasswordConfirm').value;
    
    if (!code || !newPassword || !confirmPassword) {
        alert('모든 필드를 입력하세요.');
        return;
    }
    
    if (newPassword !== confirmPassword) {
        alert('비밀번호가 일치하지 않습니다.');
        return;
    }
    
    if (newPassword.length < 4) {
        alert('비밀번호는 최소 4자 이상이어야 합니다.');
        return;
    }
    
    try {
        const response = await fetch('/api/user/update-password', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: user.id, password: newPassword, code })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            alert('비밀번호가 변경되었습니다.');
            document.getElementById('passwordVerifyCode').value = '';
            document.getElementById('newPassword').value = '';
            document.getElementById('newPasswordConfirm').value = '';
            document.getElementById('passwordChangeGroup').style.display = 'none';
        } else {
            alert(data.detail || '비밀번호 변경에 실패했습니다.');
        }
    } catch (error) {
        console.error('비밀번호 변경 오류:', error);
        alert('비밀번호 변경 중 오류가 발생했습니다.');
    }
}

// 회원 탈퇴 모달 표시
function showDeleteAccountModal() {
    document.getElementById('deleteAccountModal').style.display = 'flex';
    document.getElementById('deleteAccountPassword').value = '';
}

// 회원 탈퇴 모달 닫기
function closeDeleteAccountModal() {
    document.getElementById('deleteAccountModal').style.display = 'none';
}

// 회원 탈퇴 실행
async function performDeleteAccount() {
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    const password = document.getElementById('deleteAccountPassword').value.trim();
    
    if (!password) {
        alert('비밀번호를 입력하세요.');
        return;
    }
    
    if (!confirm('정말로 탈퇴하시겠습니까? 이 작업은 되돌릴 수 없습니다.')) {
        return;
    }
    
    try {
        const response = await fetch('/api/user/delete-account', {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: user.id,
                password: password
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            alert('회원 탈퇴가 완료되었습니다.');
            localStorage.removeItem('isLoggedIn');
            localStorage.removeItem('user');
            window.location.href = '/';
        } else {
            alert(data.detail || '회원 탈퇴에 실패했습니다.');
        }
    } catch (error) {
        console.error('회원 탈퇴 오류:', error);
        alert('회원 탈퇴 중 오류가 발생했습니다.');
    }
}

// ========== 결제 관련 함수 ==========

let selectedPlanForPayment = null;

// 결제 수단 변경 시 입력 필드 전환
function changePaymentMethod() {
    const paymentMethod = document.getElementById('paymentMethod').value;
    const cardFields = document.getElementById('cardPaymentFields');
    const bankFields = document.getElementById('bankPaymentFields');
    const phoneFields = document.getElementById('phonePaymentFields');
    
    // 모든 필드 숨기기
    if (cardFields) cardFields.style.display = 'none';
    if (bankFields) bankFields.style.display = 'none';
    if (phoneFields) phoneFields.style.display = 'none';
    
    // 선택된 결제 수단의 필드만 표시
    if (paymentMethod === 'card' && cardFields) {
        cardFields.style.display = 'block';
    } else if (paymentMethod === 'bank' && bankFields) {
        bankFields.style.display = 'block';
    } else if (paymentMethod === 'phone' && phoneFields) {
        phoneFields.style.display = 'block';
    }
}

// 결제 모달 열기
function showPaymentModal(plan) {
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    if (!user.id) {
        alert('로그인이 필요합니다.');
        window.location.href = '/login';
        return;
    }

    selectedPlanForPayment = plan;
    
    const planNames = {
        'free': '무료 플랜',
        'sentinel': 'Sentinel One +',
        'pentera': 'Pentera +',
        'premium': 'Premium +'
    };
    
    const planPrices = {
        'free': '₩0',
        'sentinel': '₩40,000',
        'pentera': '₩35,000',
        'premium': '₩65,000'
    };
    
    // 모달 정보 업데이트
    const paymentPlanName = document.getElementById('paymentPlanName');
    const paymentPlanPrice = document.getElementById('paymentPlanPrice');
    
    if (paymentPlanName) paymentPlanName.textContent = planNames[plan] || plan;
    if (paymentPlanPrice) paymentPlanPrice.textContent = planPrices[plan] || '₩0';
    
    // 모달 표시
    const modal = document.getElementById('paymentModal');
    if (modal) {
        modal.style.display = 'flex';
        // 체크박스 초기화
        const agreeCheckbox = document.getElementById('paymentAgree');
        if (agreeCheckbox) agreeCheckbox.checked = false;
        
        // 결제 수단 초기화 (신용카드 기본)
        const paymentMethodSelect = document.getElementById('paymentMethod');
        if (paymentMethodSelect) {
            paymentMethodSelect.value = 'card';
            changePaymentMethod();
        }
        
        // 휴대폰 번호 자동 채우기 (사용자 정보에서)
        const phoneNumberInput = document.getElementById('phoneNumber');
        if (phoneNumberInput && user.phone) {
            phoneNumberInput.value = user.phone;
        }
    }
}

// 결제 모달 닫기
function closePaymentModal() {
    const modal = document.getElementById('paymentModal');
    if (modal) {
        modal.style.display = 'none';
    }
    selectedPlanForPayment = null;
}

// 요금제 자세히 보기 모달 열기
function showPricingDetailModal() {
    const modal = document.getElementById('pricingDetailModal');
    if (modal) {
        modal.style.display = 'flex';
    }
}

// 요금제 자세히 보기 모달 닫기
function closePricingDetailModal() {
    const modal = document.getElementById('pricingDetailModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

// 결제 처리 (실제로는 플랜만 변경)
async function processPayment(event) {
    // 이벤트가 없으면 버튼을 찾음
    const paymentBtn = event ? event.target : document.querySelector('#paymentModal .btn-primary');
    
    const agreeCheckbox = document.getElementById('paymentAgree');
    if (!agreeCheckbox || !agreeCheckbox.checked) {
        alert('결제 정보 및 이용약관에 동의해주세요.');
        return;
    }
    
    if (!selectedPlanForPayment) {
        alert('플랜 정보가 없습니다.');
        return;
    }
    
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    if (!user.id) {
        alert('로그인이 필요합니다.');
        window.location.href = '/login';
        return;
    }
    
    try {
        // 결제 처리 중 표시
        const originalText = paymentBtn.textContent;
        paymentBtn.textContent = '처리 중...';
        paymentBtn.disabled = true;
        
        console.log('결제 요청 시작:', { user_id: user.id, new_plan: selectedPlanForPayment });
        
        // API 호출하여 플랜 변경
        const response = await fetch('/api/user/change-plan', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: user.id,
                new_plan: selectedPlanForPayment
            })
        });
        
        console.log('응답 상태:', response.status);
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('에러 응답:', errorText);
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        // 성공 메시지
        alert('결제가 완료되었습니다! 플랜이 변경되었습니다.');
        
        // 로컬 스토리지 업데이트
        user.plan = selectedPlanForPayment;
        localStorage.setItem('user', JSON.stringify(user));
        
        // 모달 닫기
        closePaymentModal();
        
        // 페이지 새로고침하여 변경사항 반영
        location.reload();
        
    } catch (error) {
        console.error('결제 처리 오류:', error);
        alert('결제 처리 중 오류가 발생했습니다: ' + error.message);
        paymentBtn.textContent = '결제하기';
        paymentBtn.disabled = false;
    }
}
