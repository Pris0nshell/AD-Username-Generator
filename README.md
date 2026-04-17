A lightweight Python tool to generate realistic Active Directory username wordlists from names and/or email addresses for use with tools like Kerbrute.

Supports multiple input formats:
```
John Smith
John,Smith
john.smith@company.com
jsmith@company.com
```

Generates common AD username formats:
```
john.smith
jsmith
johns
smithj
john_smith
john-smith
johnsmith
```
De-duplicates output

python3 AD-Username-Generator.py -i input.txt -o usernames.txt
