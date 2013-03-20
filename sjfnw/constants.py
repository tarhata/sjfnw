""" App-specific settings/constants """

FUND_EMAIL = 'Project Central <projectcentral@socialjusticefund.org>'
GRANT_EMAIL = 'Social Justice Fund Grants <grants@socialjusticefund.org>'

FUND_SUPPORT_FORM = 'https://docs.google.com/forms/d/1ssR9lwBO-8Z0qygh89Wu5XK6YwxSmjIFUtOwlJOjLWw/viewform?entry.804197744='
GRANT_SUPPORT_FORM = 'https://docs.google.com/forms/d/1SKjXMmDgXeM0IFp0yiJTJgLt6smP8b3P3dbOb4AWTck/viewform?entry.804197744='

SUPPORT_EMAIL = 'techsupport@socialjusticefund.org' #displayed on support page
SUPPORT_FORM_URL = 'https://docs.google.com/spreadsheet/viewform?formkey=dHZ2cllsc044U2dDQkx1b2s4TExzWUE6MQ'

TEST_MIDDLEWARE = ('django.middleware.common.CommonMiddleware', 'django.contrib.sessions.middleware.SessionMiddleware', 'django.contrib.auth.middleware.AuthenticationMiddleware', 'django.contrib.messages.middleware.MessageMiddleware', 'sjfnw.fund.middleware.MembershipMiddleware',)

ALLOWED_FILE_TYPES = ('jpeg', 'jpg', 'png', 'gif', 'bmp', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'pdf', 'mpeg4', 'mov', 'avi', 'wmv', 'txt')
VIEWER_FORMATS = ('doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'pdf', 'mpeg4', 'mov', 'avi', 'wmv')

TIMELINE_FIELDS = ['timeline_0', 'timeline_1', 'timeline_2', 'timeline_3', 'timeline_4', 'timeline_5', 'timeline_6', 'timeline_7', 'timeline_8', 'timeline_9', 'timeline_10', 'timeline_11', 'timeline_12', 'timeline_13', 'timeline_14'] #len 15
APP_FILE_FIELDS = ['budget', 'demographics', 'funding_sources', 'fiscal_letter', 'budget1', 'budget2', 'budget3', 'project_budget_file'] #len 8