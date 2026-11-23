CREATE TABLE paged_pages (
    test TEXT NOT NULL,
    page INTEGER NOT NULL CHECK(page >= 1),
    start_second INTEGER NOT NULL CHECK(start_second >= 0),
    end_second INTEGER NOT NULL CHECK(end_second >= start_second),
    samples TEXT NOT NULL,
    receipt TEXT NOT NULL,
    created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(test, page)
);
CREATE TABLE paged_manifests (
    test TEXT PRIMARY KEY NOT NULL,
    last_page INTEGER NOT NULL CHECK(last_page >= 1),
    lost TEXT NOT NULL,
    receipt TEXT NOT NULL,
    created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
