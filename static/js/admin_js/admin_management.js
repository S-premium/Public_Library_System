// Mobile Menu Toggle
    const menuToggle = document.getElementById("menuToggle");
    const navLinks = document.getElementById("navLinks");

    menuToggle.addEventListener("click", () => {
      navLinks.classList.toggle("active");
    });

    document.addEventListener("click", (e) => {
      if (!menuToggle.contains(e.target) && !navLinks.contains(e.target)) {
        navLinks.classList.remove("active");
      }
    });

    // Search functionality
    const searchInput = document.getElementById("searchInput");
    const tbody = document.querySelector("tbody");
    const originalRows = Array.from(tbody.querySelectorAll("tr"));

    searchInput.addEventListener("keyup", function () {
      const filter = searchInput.value.toLowerCase();
      let visibleCount = 0;

      const noDataRow = tbody.querySelector(".no-data");
      if (noDataRow) noDataRow.remove();

      originalRows.forEach(row => {
        if (row.children.length < 10) return;

        let rowText = "";
        for (let i = 0; i < 3; i++) {
          rowText += row.children[i].textContent.toLowerCase();
        }

        if (rowText.includes(filter)) {
          row.style.display = "";
          visibleCount++;
        } else {
          row.style.display = "none";
        }
      });

      if (visibleCount === 0) {
        const tr = document.createElement("tr");
        tr.classList.add("no-data");
        tr.innerHTML = `<td colspan="10" style="text-align:center; color:#fff; padding:15px;">No matching users found.</td>`;
        tbody.appendChild(tr);
      }
    });

    // Unlock user function
    function unlockUser(userId) {
      if (!confirm('Unlock this user account?')) return;

      fetch(`/unlock_user/${userId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        }
      })
      .then(response => response.json())
      .then(data => {
        if (data.success) {
          alert('User unlocked successfully!');
          location.reload();
        } else {
          alert('Error: ' + data.message);
        }
      })
      .catch(error => {
        console.error('Error:', error);
        alert('An error occurred while unlocking the user');
      });
    }

    // Reset password modal
    const resetModal = document.getElementById('resetPasswordModal');
    
    function openResetModal(userId, username) {
      document.getElementById('reset_user_id').value = userId;
      document.getElementById('reset_username').value = username;
      document.getElementById('new_password').value = '';
      document.getElementById('confirm_password').value = '';
      resetModal.style.display = 'block';
    }

    function closeResetModal() {
      resetModal.style.display = 'none';
    }

    window.addEventListener('click', (e) => {
      if (e.target === resetModal) {
        closeResetModal();
      }
    });

    // Reset password form submission
    document.getElementById('resetPasswordForm').addEventListener('submit', function(e) {
      e.preventDefault();
      
      const newPassword = document.getElementById('new_password').value;
      const confirmPassword = document.getElementById('confirm_password').value;
      
      if (newPassword !== confirmPassword) {
        alert('Passwords do not match!');
        return;
      }

      const formData = new FormData(this);

      fetch('/reset_user_password', {
        method: 'POST',
        body: formData
      })
      .then(response => response.json())
      .then(data => {
        if (data.success) {
          alert('Password reset successfully!');
          closeResetModal();
          location.reload();
        } else {
          alert('Error: ' + data.message);
        }
      })
      .catch(error => {
        console.error('Error:', error);
        alert('An error occurred while resetting the password');
      });
    });

    // Event delegation for dynamically loaded buttons
    document.addEventListener("DOMContentLoaded", () => {
      // Use event delegation on tbody for unlock buttons
      document.querySelector('tbody').addEventListener('click', (e) => {
        // Check if unlock button was clicked
        if (e.target.closest('.btn-unlock')) {
          const btn = e.target.closest('.btn-unlock');
          const userId = parseInt(btn.dataset.userId, 10);
          unlockUser(userId);
        }
        
        // Check if reset button was clicked
        if (e.target.closest('.btn-reset')) {
          const btn = e.target.closest('.btn-reset');
          const userId = parseInt(btn.dataset.userId, 10);
          const username = btn.dataset.username;
          openResetModal(userId, username);
        }
      });
    });