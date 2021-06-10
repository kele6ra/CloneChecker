# CloneChecker

Python application that checks task for unique code.

Install Python Requirements:
```pip3 install -r requirements.txt```

Download html paged with students score to `scores` page.

If you want to work with PRs you should use github token,
rename token.cfg.example to token.cfg and add token to it.

Parameters can be set in `config.cfg` file:
 - download_data (true/false) - clone student's repo to `data` directory or check remotely
 - limit (0-0.99) - percent of unique check
 - bundle_filename (string) - bundle name for concatenated files or for repo file
 - recursion_limit (integer) - limit of max recursion steps
 - task_name (string) - name of task repository
 - compare_file (string) - compare file name (bundle_filename for concatenated files)
 - concat_pattern (string) - pattern for file concatenation
 - csv_delimiter (char) - cvs delimiter for parsing

Run ```python prog.py``` to start application.

Results can be found in:
 - crosscheck.txt
 - results.csv
 - graph.graphml
