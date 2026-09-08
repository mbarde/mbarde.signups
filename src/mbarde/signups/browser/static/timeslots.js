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

  // let a click anywhere in a timeslot's row select it, instead of forcing
  // users to hit the small radio button/checkbox itself
  document.querySelectorAll('tr.slot-row').forEach(function (row) {
    row.addEventListener('click', function (event) {
      // don't hijack clicks on links (e.g. edit/view icons) or on the
      // input itself (which already toggles on its own)
      if (event.target.closest('a, input')) {
        return;
      }
      var input = row.querySelector('input[name="slotSelection"]');
      if (!input) {
        return;
      }
      input.checked = input.type === 'checkbox' ? !input.checked : true;
      input.dispatchEvent(new Event('change', { bubbles: true }));
    });
  });
});
