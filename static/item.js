var checklist_re = new RegExp(/- \[(.?)\] (.*)/);

function reset_checklist_items(description) {
  /*
    clear all checklist items
  */
  let in_lines = description.split("\n");
  var out_lines = [];
  var checklist_re = new RegExp(/- \[(.?)\] (.*)/);
  in_lines.forEach(line => {
    m = checklist_re.exec(line);
    if (m && m.length > 1) {
      let checklist_item2_text = m[2];
      out_lines.push(`- [ ] ${checklist_item2_text}`);
    }
    else {
      out_lines.push(line);
    }
  });
  return out_lines.join("\n");
}

function add_checklist_item(description, item_text) {
  /*
    add an item to the checklist after the last item
  */
  let in_lines = description.split("\n");
  var checklist_re = new RegExp(/- \[(.?)\] (.*)/);
  var checklist_last_item = "";
  in_lines.forEach(line => {
    /* find last item */
    m = checklist_re.exec(line);
    if (m && m.length > 1) {
      checklist_last_item = m[2];
    }
  });
  console.log(checklist_last_item);
  var out_lines = [];
  if(checklist_last_item) {
  in_lines.forEach(line => {
    /* add new item after last item */
    m = checklist_re.exec(line);
    out_lines.push(line);
    if(m && m.length > 1) {
      let checklist_item2_text = m[2];
      console.log(checklist_item2_text, checklist_last_item);
      if(checklist_item2_text == checklist_last_item) {
        out_lines.push(`- [ ] ${item_text}`);
      }
    }
  });
  }
  else {
    /*
      add item at the end if there are no items
    */
    out_lines = in_lines;
    out_lines.push("");
    out_lines.push(`- [ ] ${item_text}`);
  }
  return out_lines.join("\n");
}

function toggle_checklist_item(description, checklist_li) {
  /*
    toggle checkbox, both in the checklist list, and
    the item description
  */
  let checkbox_text = checklist_li.innerText;
  let checklist_li_classes = checklist_li.querySelector("i").classList;
  let is_checked = checklist_li_classes.contains("fa-check-square-o");
  if (is_checked) {
    checklist_li_classes.remove("fa-check-square-o");
    checklist_li_classes.add("fa-square-o");
  }
  else {
    checklist_li_classes.remove("fa-square-o");
    checklist_li_classes.add("fa-check-square-o");
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
      let checklist_item2_sym = m[1];
      let checklist_item2_text = m[2];
      let new_checklist_status = 'x';
      if (is_checked) {
        new_checklist_status = ' ';
      }
      if (checkbox_text.endsWith(checklist_item2_text)) {
        out_lines.push(`- [${new_checklist_status}] ${checklist_item2_text}`);
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
const checklist_items = document.querySelectorAll(".checklist_item");

checklist_items.forEach(checklist_item => {
  checklist_item.addEventListener('click', e => {
    let desc_div = document.querySelector("#description");
    let new_description = toggle_checklist_item(desc_div.textContent, e.target);
    desc_div.textContent = new_description;
  });
});

const reset_all_button = document.querySelector("#checklist_reset_all");
reset_all_button.addEventListener('click', e => {
    let desc_div = document.querySelector("#description");
    let new_description = reset_checklist_items(desc_div.textContent);
    desc_div.textContent = new_description;
});

document.querySelector("#checklist_add").addEventListener('click', e => {
  let checklist_input = document.querySelector("#checklist_add_input");
  if(! checklist_input.value) {
    return;
  }
  let desc_div = document.querySelector("#description");
  let new_description = add_checklist_item(desc_div.textContent, checklist_input.value);
  desc_div.textContent = new_description;
  checklist_input.value = "";
});

/*
  scroll description to the bottom
*/
var textarea = document.getElementById('description');
textarea.scrollTop = textarea.scrollHeight;
