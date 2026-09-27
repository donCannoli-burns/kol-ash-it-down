import <doc_edit_common.ash>;

void docedit_help() {
    print("kol-doc-edit gCLI bridge", "blue");
    print("  call doc_edit_cli.ash status");
    print("  call doc_edit_cli.ash snapshot 250");
    print("  call doc_edit_cli.ash read data/example.md");
    print("  call doc_edit_cli.ash convert data/doc_edit.md | readme.html/doc_edit.html");
    print("  call doc_edit_cli.ash convert data/doc_edit.md => readme.html/doc_edit.html");
    print("  call doc_edit_cli.ash sql SELECT id,action,status FROM events ORDER BY id DESC LIMIT 20");
    print("Recommended alias: alias docedit => call doc_edit_cli.ash %%");
    print("The | character here is a doc-edit separator, not a shell pipe.");
}

void main(string command) {
    string cmd = docedit_clean(command);
    if (cmd == "" || cmd == "help") {
        docedit_help();
        return;
    }

    string id = docedit_id();
    string marker = docedit_marker(id);

    if (cmd == "status") {
        print(marker, "blue");
        docedit_write_status(marker);
        docedit_write_job(id, "status", "", "", "", 200, marker);
        print("kol-doc-edit: status queued as " + id, "green");
        return;
    }

    if (cmd == "snapshot" || starts_with(cmd, "snapshot ")) {
        int lines = 250;
        if (starts_with(cmd, "snapshot ")) lines = to_int(docedit_clean(substring(cmd, 9)));
        if (lines < 1) lines = 250;
        print(marker, "blue");
        docedit_write_job(id, "session-tail", "", "", "", lines, marker);
        print("kol-doc-edit: session-tail job queued as " + id, "green");
        return;
    }

    if (starts_with(cmd, "read ")) {
        string source = docedit_clean(substring(cmd, 5));
        docedit_write_job(id, "read", source, "", "", 0, "");
        print("kol-doc-edit: read job queued as " + id, "green");
        return;
    }

    if (starts_with(cmd, "sql ")) {
        string sql = substring(cmd, 4);
        docedit_write_job(id, "sql", "", "", sql, 0, "");
        print("kol-doc-edit: read-only SQL job queued as " + id, "green");
        return;
    }

    if (starts_with(cmd, "convert ")) {
        string spec = substring(cmd, 8);
        int cut = index_of(spec, "=>");
        int width = 2;
        if (cut < 0) {
            cut = index_of(spec, "|");
            width = 1;
        }
        if (cut < 0) {
            print("convert requires SOURCE | TARGET or SOURCE => TARGET", "red");
            return;
        }
        string source = docedit_clean(substring(spec, 0, cut));
        string target = docedit_clean(substring(spec, cut + width));
        if (source == "" || target == "") {
            print("convert requires non-empty source and target", "red");
            return;
        }
        print(marker, "blue");
        docedit_write_job(id, "convert", source, target, "", 200, marker);
        print("kol-doc-edit: conversion queued as " + id, "green");
        return;
    }

    print("Unknown doc-edit command: " + cmd, "red");
    docedit_help();
}
