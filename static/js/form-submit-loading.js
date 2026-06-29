(function () {
  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('form[data-loading-form]').forEach(function (form) {
      form.addEventListener('submit', function (event) {
        if (form.dataset.submitLocked === '1') {
          event.preventDefault();
          return false;
        }
        form.dataset.submitLocked = '1';
        var submitBtn = form.querySelector('button[type="submit"], input[type="submit"]');
        if (submitBtn) {
          submitBtn.disabled = true;
        }
      });
    });
  });
})();
