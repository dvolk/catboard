const checklist_items = document.querySelectorAll(".checklist_item")

function toggle_checkbox(description, checkbox_li) {
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

  return out_lines.join("\n");
}

checklist_items.forEach(checklist_item => {
  checklist_item.addEventListener('click', (e) => {
    let desc_div = document.querySelector("#description");
    let new_description = toggle_checkbox(desc_div.textContent, e.target);
    desc_div.textContent = new_description;
  });
});
