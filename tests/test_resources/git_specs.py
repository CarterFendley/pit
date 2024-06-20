from .fixtures import GitSpec, GIT_CODE_COMMITTED

GIT_SPEC_ONE = GitSpec({
    # Committed files
    # Note: `99` is not valid git status code, just making up one here for use with the fixture
    GIT_CODE_COMMITTED: {
        'file_committed.txt',
    },
    # Untracked files
    '??': {
        'file_untracked.txt',
        'dir/file_one.txt',
        'dir/file_two.txt',
        # Add name edge cases
        'white   space.txt',
        '"quotes.txt"',
        '\\\\"backslash_quotes.txt\\\\"',
        # This is added automatically when adding the `ignore` option but listing here for use in tests
        '.gitignore'
    },
    # Newly added files
    'A ': {
        'file_staged.txt',
    },
    # Ignored files
    '!!': {
        'file_ignored.txt',
        'ignored_dir/file_one.txt',
        'ignored_dir/file_two.txt',
    }
})