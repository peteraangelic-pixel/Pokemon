=== kaggle --version ===
Kaggle CLI 2.2.4

=== kaggle --help ===
usage: kaggle [-h] [-v] [-W]
              {competitions,c,datasets,d,kernels,k,models,m,files,forums,f,benchmarks,b,config,auth,quota}
              ...

options:
  -h, --help            show this help message and exit
  -v, --version         Print the Kaggle CLI version
  -W, --no-warn         Disable out-of-date API version warning

commands:
  {competitions,c,datasets,d,kernels,k,models,m,files,forums,f,benchmarks,b,config,auth,quota}
                        Use one of:
                        competitions {list, files, download, submit, submissions, leaderboard, team-submissions, submission-limits, episodes, replay, logs, pages, hosts, data, settings, solution, launch, init, create, topics, topic-messages}
                        competitions topics {list, show}
                        datasets {list, files, download, create, version, init, metadata, status, delete, topics}
                        datasets topics {list, show}
                        kernels {list, files, get, init, push, pull, output, status, logs, update, delete, topics}
                        kernels topics {list, show}
                        models {instances, i, variations, v, get, list, init, create, delete, update, topics}
                        models topics {list, show}
                        models variations {versions, v, get, files, list, init, create, delete, update}
                        models variations versions {init, create, download, delete, files, list}
                        forums {list, topics}
                        forums topics {list, show}
                        benchmarks {tasks, t, auth, init, topics, leaderboard}
                        benchmarks topics {list, show}
                        config {view, set, unset}
                        auth {login, print-access-token, revoke}
                        quota
    competitions (c)    Commands related to Kaggle competitions
    datasets (d)        Commands related to Kaggle datasets
    kernels (k)         Commands related to Kaggle kernels
    models (m)          Commands related to Kaggle models
    files               Commands related files
    forums (f)          Commands related to Kaggle discussion forums
    benchmarks (b)      Commands related to Kaggle benchmarks
    config              Configuration settings
    auth                Commands related to authentication
    quota               Show the current user's weekly GPU and TPU accelerator quota

=== kaggle competitions --help ===
usage: kaggle competitions [-h]
                           {list,files,download,submit,submissions,leaderboard,team-submissions,submission-limits,episodes,replay,logs,pages,hosts,data,settings,solution,launch,init,create,topics,topic-messages}
                           ...

options:
  -h, --help            show this help message and exit

commands:
  {list,files,download,submit,submissions,leaderboard,team-submissions,submission-limits,episodes,replay,logs,pages,hosts,data,settings,solution,launch,init,create,topics,topic-messages}
    list                List available competitions
    files               List competition files
    download            Download competition files
    submit              Make a new competition submission
    submissions         Show your competition submissions
    leaderboard         Get competition leaderboard information
    team-submissions    List a team's public submissions (every active submission for simulation competitions, or the public leaderboard submission for regular competitions)
    submission-limits   Show your team's submission counts and remaining daily allowance for a competition
    episodes            List episodes for a submission in a simulation competition
    replay              Download the replay for a simulation episode
    logs                Download agent logs for a simulation episode
    pages               List pages for a competition
    hosts               List hosts (users with host access) for a competition
    data                Manage a competition's data files
    settings            Manage settings for a competition you host
    solution            Manage the private solution file for a competition you host
    launch              Launch a competition you host, optionally at a future UTC time
    init                Initialize folder with a competition-metadata.json template
    create              Create a new competition from competition-metadata.json
    topics              List discussion topics for a competition
    topic-messages      ==SUPPRESS==

=== kaggle kernels --help ===
usage: kaggle kernels [-h]
                      {list,files,get,init,push,pull,output,status,logs,update,delete,topics}
                      ...

options:
  -h, --help            show this help message and exit

commands:
  {list,files,get,init,push,pull,output,status,logs,update,delete,topics}
    list                List available kernels. By default, shows 20 results sorted by hotness
    files               List kernel output files
    init                Initialize metadata file for a kernel
    push (update)       Push new code to a kernel and run the kernel
    pull (get)          Pull down code from a kernel
    output              Get data output from the latest kernel run
    status              Display the status of the latest kernel run
    logs                Print the execution logs from the latest kernel run
    delete              Delete a kernel
    topics              List discussion topics for a kernel
=== kaggle kernels push --help ===
usage: kaggle kernels push [-h] [-p FOLDER] [-t TIMEOUT] [--accelerator ACC]

options:
  -h, --help            show this help message and exit
  -p FOLDER, --path FOLDER
                        Folder for upload, containing data files and a special kernel-metadata.json file (https://github.com/Kaggle/kaggle-cli/blob/main/docs/kernels_metadata.md). Defaults to current working directory
  -t TIMEOUT, --timeout TIMEOUT
                        Limit the run time of a kernel to the given number of seconds. The global maximum time will not be exceeded.
  --accelerator ACC     Specify the type of accelerator to use for the kernel run

=== kaggle kernels submit --help ===
usage: kaggle kernels [-h]
                      {list,files,get,init,push,pull,output,status,logs,update,delete,topics}
                      ...
kaggle kernels: error: argument command: invalid choice: 'submit' (choose from 'list', 'files', 'get', 'init', 'push', 'pull', 'output', 'status', 'logs', 'update', 'delete', 'topics')
