=== competitions submit --help ===
usage: kaggle competitions submit [-h] [-f FILE_NAME] [-k KERNEL] -m MESSAGE
                                  [-v VERSION] [-q] [--sandbox]
                                  [competition]

options:
  -h, --help            show this help message and exit
  competition           Competition URL suffix (use "kaggle competitions list" to show options)
                        If empty, the default competition will be used (use "kaggle config set competition")"
  -f FILE_NAME, --file FILE_NAME
                        File for upload (full path), or the name of the output file produced by a kernel (for code competitions)
  -k KERNEL, --kernel KERNEL
                        Name of kernel (notebook) to submit to a code competition
  -m MESSAGE, --message MESSAGE
                        Message describing this submission
  -v VERSION, --version VERSION
                        Version of kernel to submit to a code competition, e.g. "3"
  -q, --quiet           Suppress printing information about the upload/download progress
  --sandbox             Mark submission as a sandbox submission (competition hosts/admins only)

=== competitions episodes --help ===
usage: kaggle competitions episodes [-h] [-v | --format OUTPUT_FORMAT] [-q]
                                    submission_id

options:
  -h, --help            show this help message and exit
  submission_id         Submission ID (find yours with "kaggle competitions submissions <competition>")
  -v, --csv             Print results in CSV format (if not set print in table format)
  --format OUTPUT_FORMAT
                        Print results in selected format (csv, table, json). For details on advanced options, see
                        https://github.com/Kaggle/kaggle-cli/blob/main/docs/output_format.md
  -q, --quiet           Suppress printing information about the upload/download progress

=== competitions replay --help ===
usage: kaggle competitions replay [-h] [-p PATH] [-q] episode_id

options:
  -h, --help            show this help message and exit
  episode_id            Episode ID (find these with "kaggle competitions episodes <submission_id>")
  -p PATH, --path PATH  Folder where file(s) will be downloaded, defaults to current working directory
  -q, --quiet           Suppress printing information about the upload/download progress

=== competitions logs --help ===
usage: kaggle competitions logs [-h] [-p PATH] [-q] episode_id agent_index

options:
  -h, --help            show this help message and exit
  episode_id            Episode ID (find these with "kaggle competitions episodes <submission_id>")
  agent_index           Agent index (0-based position of the agent in the episode)
  -p PATH, --path PATH  Folder where file(s) will be downloaded, defaults to current working directory
  -q, --quiet           Suppress printing information about the upload/download progress

=== competitions submission-limits (read-only) ===
Submissions today: 1
Lifetime submissions: 1
Remaining today: 0
