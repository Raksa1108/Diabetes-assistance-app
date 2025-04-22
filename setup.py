import os
folders = [ 'app', 'data','datasets','function','image','notebooks']
files=[
     '.gitignore','README.md','SECURITY.md','loader.py','main.py','requirements.txt','training.py',
     'app/about.py','app/explainer.py','app/header.py','app/input.py','app/performance.py','app/perm_importance.py','app/predict.py',
     'data/base.py','data/config.py',
     'function/function.py','function/model.py','function/transformers.py'
]

for folder in folders:
      os.makedirs(folder, exist_ok=True)

for file in files:
     open(file, 'a').close()