document.addEventListener('DOMContentLoaded', function () {
  function checkCancelReservations() {
    var button = document.getElementById('btnCancelReservations');
    if (!button) {
      return;
    }
    var checked = document.querySelector('input[name="selectedSlot"]:checked');
    button.style.display = checked ? '' : 'none';
  }

  checkCancelReservations();
  document.querySelectorAll('input[name="selectedSlot"]').forEach(function (input) {
    input.addEventListener('change', checkCancelReservations);
  });

  function checkTimeslotSelection() {
    var fields = document.getElementById('personalInfoFields');
    var info = document.getElementById('selectTimeslotInfo');
    if (!fields || !info) {
      return;
    }
    var checked = document.querySelector('input[name="slotSelection"]:checked');
    fields.style.display = checked ? '' : 'none';
    info.style.display = checked ? 'none' : '';
  }

  checkTimeslotSelection();
  document.querySelectorAll('input[name="slotSelection"]').forEach(function (input) {
    input.addEventListener('change', checkTimeslotSelection);
  });
});
