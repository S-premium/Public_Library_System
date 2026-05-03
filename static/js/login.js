const getStartedBtn = document.getElementById('getStartedBtn');
    const contactBtn = document.getElementById('contactBtn');
    const createBtn = document.getElementById('createBtn');
    const formBox = document.getElementById('formBox');
    const loginForm = document.getElementById('loginForm');
    const contactForm = document.getElementById('contactForm');
    const signupForm = document.getElementById('signupForm');
    const closeForm = document.getElementById('closeForm');
    const toSignUpLink = document.getElementById('toSignUpLink');
    const toLoginLink = document.getElementById('toLoginLink');

    let current = null;

    function hideAllForms() {
      [loginForm, contactForm, signupForm].forEach(f => {
        f.style.display = 'none';
        f.classList.remove('fade-in');
      });
    }

    function showForm(key) {
      if (current === key) {
        formBox.classList.remove('active');
        current = null;
        return;
      }

      hideAllForms();

      if (key === 'login') loginForm.style.display = 'block';
      else if (key === 'contact') contactForm.style.display = 'block';
      else if (key === 'signup') signupForm.style.display = 'block';

      const visible = document.querySelector('.form-content[style*="display:block"]');
      if (visible) {
        void visible.offsetWidth;
        visible.classList.add('fade-in');
      }

      formBox.classList.add('active');
      current = key;

      const firstInput = visible && visible.querySelector('input, textarea, button');
      if (firstInput) firstInput.focus();
    }

    getStartedBtn.addEventListener('click', () => showForm('login'));
    contactBtn.addEventListener('click', () => showForm('contact'));
    createBtn.addEventListener('click', () => showForm('signup'));
    closeForm.addEventListener('click', () => {
      formBox.classList.remove('active');
      current = null;
    });

    toSignUpLink.addEventListener('click', (e) => { e.preventDefault(); showForm('signup'); });
    toLoginLink.addEventListener('click', (e) => { e.preventDefault(); showForm('login'); });

    document.getElementById('contactFormElement').addEventListener('submit', function(e) {
      e.preventDefault();
      alert('Message sent (demo)');
    });

    window.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && current) {
        formBox.classList.remove('active');
        current = null;
      }
    });

    // ========================= password detection ==========================

    function checkPasswordStrength(password) {
      const strengthText = document.getElementById("strengthText");

      const hasUpper = /[A-Z]/.test(password);
      const hasLower = /[a-z]/.test(password);
      const hasNumber = /[0-9]/.test(password);
      const hasSpecial = /[!@#$%^&*(),.?":{}|<>]/.test(password);
      const length = password.length;

      let strength = "Easy";
      strengthText.className = "strength-easy";

      if (length >= 8 && hasUpper && hasLower && hasNumber && hasSpecial) {
        strength = "Strong";
        strengthText.className = "strength-strong";
      } else if (
        length >= 6 &&
        ((hasUpper && hasLower) || (hasNumber && hasSpecial))
      ) {
        strength = "Medium";
        strengthText.className = "strength-medium";
      }

      strengthText.textContent = strength;
    }

    /* FINAL validation before submit */
    document.getElementById("signupFormElement").addEventListener("submit", function (e) {
      const password = document.getElementById("signupPassword").value;

      const valid =
        /[A-Z]/.test(password) &&
        /[a-z]/.test(password) &&
        /[0-9]/.test(password) &&
        /[!@#$%^&*(),.?":{}|<>]/.test(password) &&
        password.length >= 8;

      if (!valid) {
        e.preventDefault();
        alert(
          "Password must be at least 8 characters and include uppercase, lowercase, number, and special character."
        );
      }
    });

