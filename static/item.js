function toggle_checkbox(description, checkbox_li) {
  /*
    toggle checkbox, both in the checklist list, and
    the item description
  */
  let checkbox_text = checkbox_li.innerText;
  let checkbox_classes = checkbox_li.querySelector("i").classList;
  let is_checked = checkbox_classes.contains("fa-check-square-o");
  if (is_checked) {
    checkbox_classes.remove("fa-check-square-o");
    checkbox_classes.add("fa-square-o");
  }
  else {
    checkbox_classes.remove("fa-square-o");
    checkbox_classes.add("fa-check-square-o");
  }
  /*
    go through description lines and toggle the checklist item
  */
  let in_lines = description.split("\n");
  var out_lines = [];
  var checklist_re = new RegExp(/- \[(.?)\] (.*)/);
  in_lines.forEach(line => {
    m = checklist_re.exec(line);
    if (m && m.length > 1) {
      checkbox2_sym = m[1];
      checkbox2_text = m[2];
      new_checkbox = 'x';
      if (is_checked) {
        new_checkbox = ' ';
      }
      if (checkbox_text.endsWith(checkbox2_text)) {
        out_lines.push(`- [${new_checkbox}] ${checkbox2_text}`);
      }
      else {
        out_lines.push(line);
      }
    }
    else {
      out_lines.push(line)
    }
  });
  /*
    return the new item description with the checklist item toggled
  */
  return out_lines.join("\n");
}

function typeInTextarea(newText, el = document.activeElement) {
  /*
    insert text into textarea at cursor
  */
  const start = el.selectionStart
  const end = el.selectionEnd
  const text = el.value
  const before = text.substring(0, start)
  const after  = text.substring(end, text.length)
  el.value = (before + newText + after)
  el.selectionStart = el.selectionEnd = start + newText.length
  el.focus()
}

function insert_date() {
  /*
    insert datetime into description at cursor.
    format yyyy-mm-dd MM:SS
  */
  var today = new Date();
  var dd = String(today.getDate()).padStart(2, '0');
  var mm = String(today.getMonth() + 1).padStart(2, '0');
  var yyyy = today.getFullYear();
  var hhh = String(today.getHours()).padStart(2, '0');
  var mmm = String(today.getMinutes()).padStart(2, '0');

  today = yyyy + '-' + mm + '-' + dd + ' ' + hhh + ':' + mmm
  typeInTextarea(today, document.getElementById('description'))
}

/*
  add click event handler to checklist items
*/
const checklist_items = document.querySelectorAll(".checklist_item")

checklist_items.forEach(checklist_item => {
  checklist_item.addEventListener('click', (e) => {
    let desc_div = document.querySelector("#description");
    let new_description = toggle_checkbox(desc_div.textContent, e.target);
    desc_div.textContent = new_description;
  });
});

/*
  scroll description to the bottom
*/
var textarea = document.getElementById('description');
textarea.scrollTop = textarea.scrollHeight;
