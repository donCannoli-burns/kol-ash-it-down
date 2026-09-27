string js_escape_token(string s) {
    s = replace_string(s, "\\", "\\\\");
    s = replace_string(s, "'", "\\'");
    s = replace_string(s, "\n", "");
    s = replace_string(s, "\r", "");
    return s;
}

void main() {
    buffer page = file_to_buffer("doc_edit/ui.html");
    buffer token_buf = file_to_buffer("doc_edit/service.token");

    if (length(page) == 0) {
        write("<!doctype html><html><body><h1>kol-doc-edit</h1><p>UI missing. Run install.sh from the project checkout.</p></body></html>");
        return;
    }

    string token = js_escape_token(to_string(token_buf));
    string rendered = replace_string(to_string(page), "__KOL_DOC_EDIT_TOKEN__", token);
    write(rendered);
}
