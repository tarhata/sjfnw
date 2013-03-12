""" App-specific settings/constants """

FUND_EMAIL = 'Project Central <projectcentral@socialjusticefund.org>'
GRANT_EMAIL = 'Social Justice Fund Grants <grants@socialjusticefund.org>'

SUPPORT_EMAIL = 'techsupport@socialjusticefund.org' #displayed on support page
SUPPORT_FORM_URL = 'https://docs.google.com/spreadsheet/viewform?formkey=dHZ2cllsc044U2dDQkx1b2s4TExzWUE6MQ'

TEST_MIDDLEWARE = ('django.middleware.common.CommonMiddleware', 'django.contrib.sessions.middleware.SessionMiddleware', 'django.contrib.auth.middleware.AuthenticationMiddleware', 'django.contrib.messages.middleware.MessageMiddleware', 'sjfnw.fund.middleware.MembershipMiddleware',)

ALLOWED_FILE_TYPES = ('jpeg', 'jpg', 'png', 'gif', 'bmp', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'pdf', 'mpeg4', 'mov', 'avi', 'wmv', 'txt')
VIEWER_FORMATS = ('doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'pdf', 'mpeg4', 'mov', 'avi', 'wmv')

TIMELINE_FIELDS = ['timeline_1_date', 'timeline_1_activities', 'timeline_1_goals', 'timeline_2_date', 'timeline_2_activities', 'timeline_2_goals', 'timeline_3_date', 'timeline_3_activities', 'timeline_3_goals', 'timeline_4_date', 'timeline_4_activities', 'timeline_4_goals', 'timeline_5_date', 'timeline_5_activities', 'timeline_5_goals'] #len 15
APP_FILE_FIELDS = ['budget', 'demographics', 'funding_sources', 'fiscal_letter', 'budget1', 'budget2', 'budget3', 'project_budget_file'] #len 8