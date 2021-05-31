# CloneChecker

Python application that checks task for uniqe code.

Install Python Requirements:
```pip3 install -r requirements.txt```

Download html paged with students score to `scores` page.

Parameters can be set in `config.cfg` file:
 - download_data (true/false) - clone student's repo to `data` direcory or check remotely
 - limit (0-0.99) - percent of unique check
 - bundle_filename (string) - bundle name for python binary
 - recursion_limit (integer) - limit of max recursion steps
 - task_name (string) - name of task repository
 - entery point (string) - entery point file or directory name

Run ```python prog.py``` to start application.

Results can be found in:
 - crosscheck.txt
 - results.csv
 - graph.graphml
