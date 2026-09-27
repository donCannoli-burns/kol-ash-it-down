string docedit_json_escape(string s) {
    s = replace_string(s, "\\", "\\\\");
    s = replace_string(s, "\"", "\\\"");
    s = replace_string(s, "\n", "\\n");
    s = replace_string(s, "\r", "\\r");
    s = replace_string(s, "\t", "\\t");
    return s;
}

string docedit_clean(string s) {
    while (length(s) > 0 && starts_with(s, " ")) s = substring(s, 1);
    while (length(s) > 0 && substring(s, length(s) - 1) == " ") s = substring(s, 0, length(s) - 1);
    return s;
}

string docedit_id() {
    return now_to_string("yyyyMMddHHmmss") + "-" + my_id() + "-" + random(1000000);
}

string docedit_marker(string id) {
    return "KOL_DOC_EDIT_GCLI|" + my_name() + "|" + id;
}

boolean docedit_write_job(string id, string action, string source, string target, string payload, int lines, string marker) {
    string json = "{";
    json += "\"id\":\"" + docedit_json_escape(id) + "\",";
    json += "\"correlation_id\":\"" + docedit_json_escape(id) + "\",";
    json += "\"action\":\"" + docedit_json_escape(action) + "\",";
    json += "\"player\":\"" + docedit_json_escape(my_name()) + "\",";
    json += "\"source\":\"" + docedit_json_escape(source) + "\",";
    json += "\"target\":\"" + docedit_json_escape(target) + "\",";
    json += "\"payload\":\"" + docedit_json_escape(payload) + "\",";
    json += "\"lines\":" + lines + ",";
    json += "\"marker\":\"" + docedit_json_escape(marker) + "\"";
    json += "}\n";
    return buffer_to_file(json.to_buffer(), "doc_edit/inbox/" + id + ".json");
}

void docedit_write_status(string marker) {
    string json = "{";
    json += "\"schema\":\"kol-doc-edit/ash-status-v1\",";
    json += "\"generated_at\":\"" + docedit_json_escape(now_to_string("yyyy-MM-dd'T'HH:mm:ss")) + "\",";
    json += "\"player\":\"" + docedit_json_escape(my_name()) + "\",";
    json += "\"player_id\":" + my_id() + ",";
    json += "\"class\":\"" + docedit_json_escape(to_string(my_class())) + "\",";
    json += "\"level\":" + my_level() + ",";
    json += "\"path\":\"" + docedit_json_escape(to_string(my_path())) + "\",";
    json += "\"adventures\":" + my_adventures() + ",";
    json += "\"meat\":" + my_meat() + ",";
    json += "\"ascensions\":" + my_ascensions() + ",";
    json += "\"daycount\":" + daycount() + ",";
    json += "\"turns_played\":" + turns_played() + ",";
    json += "\"can_interact\":" + to_string(can_interact()) + ",";
    json += "\"marker\":\"" + docedit_json_escape(marker) + "\"";
    json += "}\n";
    buffer_to_file(json.to_buffer(), "doc_edit/system-status.json");
}