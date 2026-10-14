# scripts

## leak_check.py

`leak_check.py` checks a repository and its whole history for the terms you list, including old commits. Run it before you make a copy public.

It needs Python 3.9 or newer and git. It scans the following.

- Every file in every commit on every branch and tag, and the file names.
- Every commit message, and every author and committer name and email.
- Every tag name, tag message and tagger, and every branch name.

### Keep the denylist outside the repo

The list of terms is itself personal, so it never goes in the repo. Keep it in a file of your own, for example `~/private/denylist.txt`.

```text
# one term per line
jane example
jane@example.com
re:555-01\d\d
```

- Blank lines and lines starting with `#` are ignored.
- A plain line is a case-insensitive literal.
- A line starting with `re:` is a case-insensitive regular expression.
- Surrounding spaces are trimmed. Use `\s` in a regular expression when a space matters.

### Run the check

Use a full clone. A shallow clone has no old commits, and the script warns when it sees one.

```sh
python3 scripts/leak_check.py --denylist ~/private/denylist.txt
python3 scripts/leak_check.py --denylist ~/private/denylist.txt --repo ../other-copy
```

Do not run it in CI with a denylist, because the list would have to be stored there.

### Read the output

Each hit is one line. The script never prints the matched text or the line it was in, so a terminal or CI log does not repeat the leak.

```text
3f2a9b1 notes.txt:2 denylist:3
msg 3f2a9b1:1 denylist:1
author 3f2a9b1:committer-email denylist:2
tag 9c04d7e:name denylist:1
```

| Line starts with | Meaning |
|---|---|
| a short sha, then a path and a line number | that line of that file, in the first commit that has it. `git show 3f2a9b1:notes.txt` shows it |
| a short sha, then a path and `path` | the file name itself matched. The line shows `blob-<id>` in place of the name, unless you pass `--show` |
| `msg` | that line of the commit message |
| `author` | `author-name`, `author-email`, `committer-name` or `committer-email` of the commit |
| `tag` | the tag, by the id of its tag object, or of the commit for a lightweight tag. `git for-each-ref --points-at 9c04d7e` finds it |
| `branch` | the branch, by the commit it points at |

`denylist:3` is the line number in your denylist file, counting blank and comment lines.

A summary goes to stderr, including how many binary files were skipped. `--show` adds the matched text to each line. Use it only on your own machine.

The exit status is 0 when clean, 1 when there are hits and 2 for bad usage, such as a missing file or a bad regular expression.

### Allow a known match

Some matches are fine, such as your name in `LICENSE`. List them in an allow file and pass it with `--allow`. Each line is a path glob, a tab, then the exact text. Blank lines and lines starting with `#` are ignored.

```text
LICENSE	Jane Example
*	example-org/example-app
git:author	Jane Example
```

- A match counts unless it falls entirely inside the allowed text on its line. A match that sticks out of it still counts.
- The text is case sensitive.
- The glob is matched against the whole path, and `*` also matches `/`.
- For text outside files, use the globs `git:msg`, `git:author`, `git:tag` and `git:branch`. `*` matches all of them. `git:author` also covers the name and email of a tagger.

### What it does not catch

- Binary files are not read. A file with a NUL byte in its first 8000 bytes counts as binary, which includes UTF-16 text. Images and PDFs can carry names in their metadata, so check them by hand.
- The signature block of a signed tag is not read.
- Terms are matched one line at a time, so a term split over two lines is missed.
- Accented letters in a different Unicode form do not match. List both spellings. Text that is not UTF-8 is read with replacement characters, so accented terms in it may not match.
- It finds only what you list. It does not remove anything. Removing an old hit means rewriting history.

## Tests

```sh
python3 -m unittest discover -s scripts -v
```
