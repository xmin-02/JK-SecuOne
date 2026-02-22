// 전역 변수
let emailVerified = false;
let usernameChecked = false;
let verificationCodeSent = false;

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', () => {
    initializeFormValidation();
});

// 폼 검증 초기화
function initializeFormValidation() {
    const phone = document.getElementById('phone');
    const password = document.getElementById('password');
    const passwordConfirm = document.getElementById('passwordConfirm');
    const username = document.getElementById('username');
    
    // 연락처 자동 포맷팅
    phone.addEventListener('input', formatPhoneNumber);
    
    // 비밀번호 강도 체크
    password.addEventListener('input', checkPasswordStrength);
    
    // 비밀번호 확인
    passwordConfirm.addEventListener('input', checkPasswordMatch);
    
    // 아이디 입력 시 중복확인 초기화
    username.addEventListener('input', () => {
        usernameChecked = false;
        updateSignupButton();
    });
    
    // 이메일 입력 시 인증 초기화
    document.getElementById('email').addEventListener('input', () => {
        emailVerified = false;
        verificationCodeSent = false;
        document.getElementById('verificationCodeGroup').classList.remove('show');
        updateSignupButton();
    });
}

// 연락처 포맷팅 (010-0000-0000)
function formatPhoneNumber(e) {
    let value = e.target.value.replace(/[^0-9]/g, '');
    
    if (value.length <= 3) {
        e.target.value = value;
    } else if (value.length <= 7) {
        e.target.value = value.slice(0, 3) + '-' + value.slice(3);
    } else {
        e.target.value = value.slice(0, 3) + '-' + value.slice(3, 7) + '-' + value.slice(7, 11);
    }
}

// 이메일 인증번호 발송
async function sendVerificationCode() {
    const email = document.getElementById('email').value;
    const emailHelpText = document.getElementById('emailHelpText');
    const sendCodeBtn = document.getElementById('sendCodeBtn');
    
    if (!email) {
        emailHelpText.textContent = '이메일을 입력해주세요.';
        emailHelpText.className = 'help-text error';
        return;
    }
    
    // 이메일 형식 검증
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
        emailHelpText.textContent = '올바른 이메일 형식이 아닙니다.';
        emailHelpText.className = 'help-text error';
        return;
    }
    
    sendCodeBtn.disabled = true;
    sendCodeBtn.textContent = '발송중...';
    emailHelpText.textContent = '인증번호를 발송하고 있습니다...';
    emailHelpText.className = 'help-text';
    
    try {
        const response = await fetch('/api/auth/send-verification', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ email })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            emailHelpText.textContent = '인증번호가 발송되었습니다. 이메일을 확인해주세요.';
            emailHelpText.className = 'help-text success';
            
            // 인증번호 입력란 표시
            document.getElementById('verificationCodeGroup').classList.add('show');
            verificationCodeSent = true;
            sendCodeBtn.textContent = '재발송';
        } else {
            emailHelpText.textContent = result.detail || '인증번호 발송에 실패했습니다.';
            emailHelpText.className = 'help-text error';
            sendCodeBtn.textContent = '인증';
        }
    } catch (error) {
        console.error('인증번호 발송 오류:', error);
        emailHelpText.textContent = '서버 오류가 발생했습니다.';
        emailHelpText.className = 'help-text error';
        sendCodeBtn.textContent = '인증';
    } finally {
        sendCodeBtn.disabled = false;
    }
}

// 인증번호 확인
async function verifyCode() {
    const email = document.getElementById('email').value;
    const code = document.getElementById('verificationCode').value;
    const codeHelpText = document.getElementById('codeHelpText');
    
    if (!code) {
        codeHelpText.textContent = '인증번호를 입력해주세요.';
        codeHelpText.className = 'help-text error';
        return;
    }
    
    if (code.length !== 6) {
        codeHelpText.textContent = '인증번호는 6자리입니다.';
        codeHelpText.className = 'help-text error';
        return;
    }
    
    try {
        const response = await fetch('/api/auth/verify-code', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ email, code })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            codeHelpText.textContent = '이메일 인증이 완료되었습니다.';
            codeHelpText.className = 'help-text success';
            document.getElementById('verificationCode').classList.add('success');
            document.getElementById('email').classList.add('success');
            emailVerified = true;
            updateSignupButton();
        } else {
            codeHelpText.textContent = result.detail || '인증번호가 일치하지 않습니다.';
            codeHelpText.className = 'help-text error';
            document.getElementById('verificationCode').classList.add('error');
        }
    } catch (error) {
        console.error('인증번호 확인 오류:', error);
        codeHelpText.textContent = '서버 오류가 발생했습니다.';
        codeHelpText.className = 'help-text error';
    }
}

// 아이디 중복 체크
async function checkUsername() {
    const username = document.getElementById('username').value;
    const usernameHelpText = document.getElementById('usernameHelpText');
    
    if (!username) {
        usernameHelpText.textContent = '아이디를 입력해주세요.';
        usernameHelpText.className = 'help-text error';
        return;
    }
    
    // 아이디 형식 검증 (영문, 숫자 4-20자)
    const usernameRegex = /^[a-zA-Z0-9]{4,20}$/;
    if (!usernameRegex.test(username)) {
        usernameHelpText.textContent = '아이디는 영문, 숫자 조합 4-20자로 입력해주세요.';
        usernameHelpText.className = 'help-text error';
        return;
    }
    
    try {
        const response = await fetch('/api/auth/check-username', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username })
        });
        
        const result = await response.json();
        
        if (result.available) {
            usernameHelpText.textContent = '사용 가능한 아이디입니다.';
            usernameHelpText.className = 'help-text success';
            document.getElementById('username').classList.add('success');
            usernameChecked = true;
            updateSignupButton();
        } else {
            usernameHelpText.textContent = '이미 사용 중인 아이디입니다.';
            usernameHelpText.className = 'help-text error';
            document.getElementById('username').classList.add('error');
            usernameChecked = false;
            updateSignupButton();
        }
    } catch (error) {
        console.error('아이디 중복 체크 오류:', error);
        usernameHelpText.textContent = '서버 오류가 발생했습니다.';
        usernameHelpText.className = 'help-text error';
    }
}

// 비밀번호 강도 체크
function checkPasswordStrength() {
    const password = document.getElementById('password').value;
    const strengthFill = document.getElementById('strengthFill');
    const passwordHelpText = document.getElementById('passwordHelpText');
    
    if (!password) {
        strengthFill.className = 'strength-fill';
        passwordHelpText.textContent = '';
        return;
    }
    
    let strength = 0;
    
    // 길이
    if (password.length >= 8) strength++;
    if (password.length >= 12) strength++;
    
    // 영문
    if (/[a-zA-Z]/.test(password)) strength++;
    
    // 숫자
    if (/[0-9]/.test(password)) strength++;
    
    // 특수문자
    if (/[!@#$%^&*(),.?":{}|<>]/.test(password)) strength++;
    
    if (strength <= 2) {
        strengthFill.className = 'strength-fill weak';
        passwordHelpText.textContent = '약한 비밀번호입니다.';
        passwordHelpText.className = 'help-text error';
    } else if (strength <= 4) {
        strengthFill.className = 'strength-fill medium';
        passwordHelpText.textContent = '보통 비밀번호입니다.';
        passwordHelpText.className = 'help-text';
    } else {
        strengthFill.className = 'strength-fill strong';
        passwordHelpText.textContent = '강한 비밀번호입니다.';
        passwordHelpText.className = 'help-text success';
    }
}

// 비밀번호 일치 확인
function checkPasswordMatch() {
    const password = document.getElementById('password').value;
    const passwordConfirm = document.getElementById('passwordConfirm').value;
    const passwordConfirmHelpText = document.getElementById('passwordConfirmHelpText');
    
    if (!passwordConfirm) {
        passwordConfirmHelpText.textContent = '';
        document.getElementById('passwordConfirm').classList.remove('success', 'error');
        return;
    }
    
    if (password === passwordConfirm) {
        passwordConfirmHelpText.textContent = '비밀번호가 일치합니다.';
        passwordConfirmHelpText.className = 'help-text success';
        document.getElementById('passwordConfirm').classList.remove('error');
        document.getElementById('passwordConfirm').classList.add('success');
    } else {
        passwordConfirmHelpText.textContent = '비밀번호가 일치하지 않습니다.';
        passwordConfirmHelpText.className = 'help-text error';
        document.getElementById('passwordConfirm').classList.remove('success');
        document.getElementById('passwordConfirm').classList.add('error');
    }
}

// 회원가입 버튼 활성화 체크
function updateSignupButton() {
    const signupBtn = document.getElementById('signupBtn');
    signupBtn.disabled = !(emailVerified && usernameChecked);
}

// 회원가입 처리
async function handleSignup(event) {
    event.preventDefault();
    
    // 최종 검증
    if (!emailVerified) {
        alert('이메일 인증을 완료해주세요.');
        return;
    }
    
    if (!usernameChecked) {
        alert('아이디 중복 확인을 해주세요.');
        return;
    }
    
    const password = document.getElementById('password').value;
    const passwordConfirm = document.getElementById('passwordConfirm').value;
    
    if (password !== passwordConfirm) {
        alert('비밀번호가 일치하지 않습니다.');
        return;
    }
    
    const signupData = {
        name: document.getElementById('name').value,
        phone: document.getElementById('phone').value,
        email: document.getElementById('email').value,
        username: document.getElementById('username').value,
        password: password
    };
    
    const signupBtn = document.getElementById('signupBtn');
    signupBtn.disabled = true;
    signupBtn.textContent = '가입 처리 중...';
    
    try {
        const response = await fetch('/api/auth/signup', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(signupData)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            alert('회원가입이 완료되었습니다! 로그인 페이지로 이동합니다.');
            window.location.href = '/login';
        } else {
            alert(result.detail || '회원가입에 실패했습니다.');
            signupBtn.disabled = false;
            signupBtn.textContent = '회원가입';
        }
    } catch (error) {
        console.error('회원가입 오류:', error);
        alert('서버 오류가 발생했습니다.');
        signupBtn.disabled = false;
        signupBtn.textContent = '회원가입';
    }
}
