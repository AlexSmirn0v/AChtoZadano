import os

def subjects_tokens():
    subs = dict()
    with open(os.path.join(os.path.dirname(os.path.dirname(__file__)), "db_modules", "def_data", "subjects.txt"), encoding='utf8') as text:
        for line in text.readlines():
            if not line.startswith("ИНФОРМАЦИЯ"):
                sub_name, sub_token, sub_name_datv = line.strip().split('-')
                if sub_name.endswith('группа'):
                    sub_token_1 = sub_token[:-1] + '1'
                    sub_token_2 = sub_token[:-1] + '2'
                else:
                    sub_token_1 = sub_token
                    sub_token_2 = sub_token
                sub_name = sub_name.split(' ')[0] 
                subs[sub_name.lower()] = [sub_token_1, sub_token_2]
                subs[sub_name_datv.lower()] = [sub_token_1, sub_token_2]
    return subs

print(subjects_tokens())