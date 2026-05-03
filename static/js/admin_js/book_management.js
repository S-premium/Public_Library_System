    const menuToggle = document.getElementById("menuToggle");
    const navLinks = document.getElementById("navLinks");

    menuToggle.addEventListener("click", () => {
      navLinks.classList.toggle("active");
    });

    // Close menu when clicking outside
    document.addEventListener("click", (e) => {
      if (!menuToggle.contains(e.target) && !navLinks.contains(e.target)) {
        navLinks.classList.remove("active");
      }
    });

    // Close menu when clicking a link (except dropdowns)
    navLinks.querySelectorAll("a:not(.dropdown-toggle)").forEach(link => {
      link.addEventListener("click", () => {
        navLinks.classList.remove("active");
      });
    });


    const searchInput = document.getElementById("searchInput");
    const tbody = document.querySelector("tbody");

    // Save the original rows
    const originalRows = Array.from(tbody.querySelectorAll("tr"));

    searchInput.addEventListener("keyup", function () {
      const filter = searchInput.value.toLowerCase();
      let visibleCount = 0;

      // Remove previous "no matching books" row
      const noDataRow = tbody.querySelector(".no-data");
      if (noDataRow) noDataRow.remove();

      // Show/hide rows based on search
      originalRows.forEach(row => {
        if (row.children.length < 8) return; // skip any placeholder rows

        let rowText = "";
        for (let i = 0; i < 7; i++) {
          rowText += row.children[i].textContent.toLowerCase();
        }

        if (rowText.includes(filter)) {
          row.style.display = "";
          visibleCount++;
        } else {
          row.style.display = "none";
        }
      });

      // If no rows are visible, show "No matching books found"
      if (visibleCount === 0) {
        const tr = document.createElement("tr");
        tr.classList.add("no-data");
        tr.innerHTML = `<td colspan="8" style="text-align:center; color:#fff; padding:15px;">No matching books found.</td>`;
        tbody.appendChild(tr);
      }
    });


    const addBookBtn = document.getElementById("addBookBtn");
    const addBookModal = document.getElementById("addBookModal");
    const closeModal = document.querySelector(".close-modal");

    // Open modal
    addBookBtn.addEventListener("click", () => {
      addBookModal.style.display = "block";
    });

    // Close modal on X
    closeModal.addEventListener("click", () => {
      addBookModal.style.display = "none";
    });

    // Close modal on outside click
    window.addEventListener("click", (e) => {
      if (e.target == addBookModal) {
        addBookModal.style.display = "none";
      }
    });

    document.getElementById('addBookForm').addEventListener('submit', function(e) {
        const submitBtn = document.getElementById('submitBtn');
        const btnText = document.getElementById('btnText');
        const btnLoader = document.getElementById('btnLoader');
        
        // Disable button and show loading state
        submitBtn.disabled = true;
        btnText.style.display = 'none';
        btnLoader.style.display = 'inline';
    });

    //====================== Delete selected books functionality ==================================s
    document.addEventListener('DOMContentLoaded', function() {
    const deleteBtn = document.getElementById('deleteSelectedBtn');
    const selectedCountSpan = document.getElementById('selectedCount');
    const checkboxes = document.querySelectorAll('.custom-checkbox');
    
    // Update delete button visibility and count
    function updateDeleteButton() {
        const checkedBoxes = document.querySelectorAll('.custom-checkbox:checked');
        const count = checkedBoxes.length;
        
        selectedCountSpan.textContent = count;
        
        if (count > 0) {
        deleteBtn.classList.add('show');
        } else {
        deleteBtn.classList.remove('show');
        }
    }
    
    // Add change event to all checkboxes
    checkboxes.forEach(checkbox => {
        checkbox.addEventListener('change', updateDeleteButton);
    });
    
    // Delete selected books
    deleteBtn.addEventListener('click', async function() {
        const checkedBoxes = document.querySelectorAll('.custom-checkbox:checked');
        const count = checkedBoxes.length;
        
        if (count === 0) return;
        
        const confirmDelete = confirm(`Are you sure you want to delete ${count} book${count > 1 ? 's' : ''}?`);
        
        if (confirmDelete) {
        deleteBtn.disabled = true;
        deleteBtn.classList.add('deleting');
        
        const bookIds = [];
        
        // Collect all checked book IDs
        checkedBoxes.forEach(checkbox => {
            const row = checkbox.closest('tr');
            const bookId = row.getAttribute('data-book-id');
            if (bookId) {
            bookIds.push(bookId);
            }
        });
        
        // Delete books one by one using your existing endpoint
        let successCount = 0;
        let errorCount = 0;
        
        for (const bookId of bookIds) {
            try {
            const response = await fetch(`/delete_book/${bookId}`, {
                method: 'POST',
                headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                }
            });
            
            if (response.ok) {
                successCount++;
                // Remove the row from the table
                const row = document.querySelector(`tr[data-book-id="${bookId}"]`);
                if (row) {
                row.style.opacity = '0';
                row.style.transform = 'translateX(-20px)';
                setTimeout(() => row.remove(), 300);
                }
            } else {
                errorCount++;
            }
            } catch (error) {
            console.error('Error deleting book:', error);
            errorCount++;
            }
        }
        
        // Show result message
        setTimeout(() => {
            deleteBtn.disabled = false;
            deleteBtn.classList.remove('deleting');
            updateDeleteButton();
            
            if (successCount > 0) {
            alert(`Successfully deleted ${successCount} book${successCount > 1 ? 's' : ''}!${errorCount > 0 ? ` (${errorCount} failed)` : ''}`);
            } else {
            alert('Failed to delete books. Please try again.');
            }
        }, 300);
        }
    });
    });



    // ==================================== Update Book Modal Functionality ===============================================
(function() {
  const updateModal = document.getElementById('updateBookModal');
  const closeUpdateModal = document.getElementById('closeUpdateModal');
  const updateForm = document.getElementById('updateBookForm');
  const updateSubmitBtn = document.getElementById('updateSubmitBtn');
  const updateBtnText = document.getElementById('updateBtnText');
  const updateBtnLoader = document.getElementById('updateBtnLoader');

  // Open update modal and populate with book data
  window.openUpdateModal = function(bookId) {
    // Get the book row data
    const row = document.querySelector(`tr[data-book-id="${bookId}"]`);
    if (!row) return;

    const cells = row.querySelectorAll('td');
    
    // Populate form fields (adjust indices based on your table structure)
    document.getElementById('update_book_id').value = bookId;
    document.getElementById('update_title').value = cells[1].textContent.trim();
    document.getElementById('update_author').value = cells[2].textContent.trim();
    document.getElementById('update_isbn').value = cells[3].textContent.trim();
    document.getElementById('update_category').value = cells[4].textContent.trim();
    document.getElementById('update_genre').value = cells[5].textContent.trim();
    document.getElementById('update_publisher').value = cells[6].textContent.trim();

    // Show modal
    updateModal.style.display = 'block';
    
    // Add entrance animation
    setTimeout(() => {
      updateModal.querySelector('.modal-content').style.animation = 'slideDown 0.3s ease';
    }, 10);
  };

  // Close modal
  closeUpdateModal.addEventListener('click', function() {
    updateModal.style.display = 'none';
  });

  // Close on outside click
  window.addEventListener('click', function(e) {
    if (e.target === updateModal) {
      updateModal.style.display = 'none';
    }
  });

  // Form submission
  updateForm.addEventListener('submit', function(e) {
    e.preventDefault();
    
    // Show loader
    updateBtnText.style.display = 'none';
    updateBtnLoader.style.display = 'inline-block';
    updateSubmitBtn.disabled = true;

    // Prepare form data
    const formData = new FormData(updateForm);

    // Send update request
    fetch('/update_book', {
      method: 'POST',
      body: formData
    })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        // Show success message
        alert('Book updated successfully!');
        
        // Reload page to show updated data
        window.location.reload();
      } else {
        alert('Error: ' + (data.message || 'Failed to update book'));
        
        // Reset button
        updateBtnText.style.display = 'inline-block';
        updateBtnLoader.style.display = 'none';
        updateSubmitBtn.disabled = false;
      }
    })
    .catch(error => {
      console.error('Error:', error);
      alert('An error occurred while updating the book');
      
      // Reset button
      updateBtnText.style.display = 'inline-block';
      updateBtnLoader.style.display = 'none';
      updateSubmitBtn.disabled = false;
    });
  });

  // Animation keyframes
  const style = document.createElement('style');
  style.textContent = `
    @keyframes slideDown {
      from {
        transform: translateY(-20px);
        opacity: 0;
      }
      to {
        transform: translateY(0);
        opacity: 1;
      }
    }
  `;
  document.head.appendChild(style);
})();

// Modify existing Update buttons to use the modal
document.addEventListener('DOMContentLoaded', function() {
  // Get all update button links
  const updateLinks = document.querySelectorAll('a[href^="/edit_book/"]');
  
  updateLinks.forEach(link => {
    // Extract book ID from href (e.g., "/edit_book/123" -> "123")
    const href = link.getAttribute('href');
    const bookId = href.split('/').pop();
    
    // Add click handler
    link.addEventListener('click', function(e) {
      e.preventDefault(); // Prevent navigation
      openUpdateModal(bookId);
    });
  });
});