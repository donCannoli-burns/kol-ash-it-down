import <doc_edit_common.ash>;

void main() {
    string id = docedit_id();
    string marker = docedit_marker(id);

    print(marker, "blue");
    docedit_write_status(marker);
    boolean queued = docedit_write_job(id, "login-sync", "", "", "", 250, marker);

    if (queued) {
        print("kol-doc-edit: login status queued for local document bridge.", "green");
    } else {
        print("kol-doc-edit: could not queue login status job.", "red");
    }
}
