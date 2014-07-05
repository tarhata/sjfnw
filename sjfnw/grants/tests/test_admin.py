
@override_settings(MIDDLEWARE_CLASSES = TEST_MIDDLEWARE)
class Reporting(BaseGrantTestCase):
  """ Admin reporting on applications, awards and organizations

  Fields can just be tested once; filters should be tested in combinations
  Fixtures include unicode characters
  """

  fixtures = LIVE_FIXTURES
  url = reverse('sjfnw.grants.views.grants_report')
  template_success = 'grants/report_results.html'
  template_error = 'grants/reporting.html'

  def setUp(self): #don't super, can't set cycle dates with this fixture
    self.logInAdmin()

  def fill_report_form(self, form, filters=False, fields=False, fmt='browse'):
    """ Shared method to create POST data for the given form

    Methods need to insert report type key themselves
    Set up to handle:
      boolean
      select fields
      year min & max
      organization_name & city (all other chars are blank)

    Args:
      form: form instance to populate
      filters: True = select all filters, False = select none
      fields: True = select all fields, TODO False = select none
      fmt: browse or csv option in form

    Returns:
      Dictionary that should be a valid POST submission for the given form
    """

    post_dict = {}
    for bfield in form:
      field = bfield.field
      name = bfield.name
      # fields
      if fields and name.startswith('report'):
        if isinstance(field, forms.BooleanField):
          post_dict[name] = True
        elif isinstance(field, forms.MultipleChoiceField):
          post_dict[name] = [val[0] for val in field.choices]
        else:
          logger.error('Unexpected field type: ' + str(field))
      # filters
      else:
        if isinstance(field, forms.BooleanField):
          post_dict[name] = True if filters else False
        elif isinstance(field, forms.MultipleChoiceField):
          post_dict[name] = [field.choices[0][0], field.choices[1][0]] if filters else []
        elif name.startswith('year_m'):
          if name == 'year_min':
            post_dict[name] = 1995
          else:
            post_dict[name] = timezone.now().year
        elif isinstance(field, forms.CharField):
          if filters:
            if name == 'organization_name':
              post_dict[name] = 'Foundation'
            elif name == 'city':
              post_dict[name] = 'Seattle'
          else:
            post_dict[name] = ''
        elif name == 'registered':
          post_dict[name] = True if filters else None
        else:
          logger.warning('Unexpected field type: ' + str(field))

    post_dict['format'] = fmt
    return post_dict


  def test_app_fields(self):
    """ Verify that application fields are fetched for browsing without error

    Setup:
      No filters selected
      All fields selected
      Format = browse

    Asserts:
      Basic success: 200 status, correct template
      Number of rows in results == number of apps in database

    """

    form = AppReportForm()
    post_dict = self.fill_report_form(form, fields=True)
    post_dict['run-application'] = '' # simulate dropdown at top of page

    response = self.client.post(self.url, post_dict)

    self.assertEqual(response.status_code, 200)
    self.assertTemplateUsed(response, self.template_success)

    results = response.context['results']
    self.assertEqual(len(results), models.GrantApplication.objects.count())

  def test_app_fields_csv(self):
    """ Verify that application fields are fetched in csv format without error

    Setup:
      No filters selected
      All fields selected
      Format = csv

    Asserts:
      Basic success: able to iterate through response with reader
      Number of rows in results matches number of apps in database
    """

    form = AppReportForm()
    post_dict = self.fill_report_form(form, fields=True, fmt='csv')
    post_dict['run-application'] = '' # simulate dropdown at top of page

    response = self.client.post(self.url, post_dict)

    reader = unicodecsv.reader(response, encoding = 'utf8')
    row_count = sum(1 for row in reader)
    # 1st row is blank, 2nd is headers
    self.assertEqual(row_count-2, models.GrantApplication.objects.count())

  def test_app_filters_all(self):
    """ Verify that all filters can be selected without error

    Setup:
      All fields
      All filters
      Format = browse

    Asserts:
      Basic success: 200 status, correct template
      Number of rows in results == number of apps in database
    """

    form = AppReportForm()
    post_dict = self.fill_report_form(form, fields=True, filters=True)
    post_dict['run-application'] = ''

    response = self.client.post(self.url, post_dict)

    self.assertEqual(200, response.status_code)
    self.assertTemplateUsed(response, self.template_success)

    results = response.context['results']
    self.assertEqual(results, [])

  def test_award_fields(self):
    """ Verify that award fields can be fetched

    Setup:
      No filters selected
      All fields selected
      Format = browse

    Asserts:
      Basic success: 200 status, correct template
      Number of rows in results == number of awards (gp + sponsored) in db
    """

    form = AwardReportForm()
    post_dict = self.fill_report_form(form, fields=True)
    post_dict['run-award'] = ''

    response = self.client.post(self.url, post_dict)

    self.assertEqual(response.status_code, 200)
    self.assertTemplateUsed(response, self.template_success)

    results = response.context['results']
    self.assertEqual(len(results),
        models.GivingProjectGrant.objects.count() + models.SponsoredProgramGrant.objects.count())

  def test_award_fields_csv(self):
    """ Verify that award fields can be fetched in csv format

    Setup:
      No filters selected
      All fields selected
      Format = browse

    Asserts:
      Basic success: able to iterate through response with reader
      Number of rows in results matches number of awards (gp + sponsored) in db

    """

    form = AwardReportForm()
    post_dict = self.fill_report_form(form, fields=True, fmt='csv')
    post_dict['run-award'] = ''

    response = self.client.post(self.url, post_dict)

    reader = unicodecsv.reader(response, encoding = 'utf8')
    row_count = sum(1 for row in reader)
    self.assertEqual(row_count-2,
        models.GivingProjectGrant.objects.count() + models.SponsoredProgramGrant.objects.count())

  def test_award_filters_all(self):
    """ Verify that all filters can be selected in award report without error

    Setup:
      All fields
      All filters
      Format = browse

    Asserts:
      Basic success: 200 status, correct template
    """

    form = AwardReportForm()
    post_dict = self.fill_report_form(form, fields=True, filters=True)
    post_dict['run-award'] = ''

    response = self.client.post(self.url, post_dict)

    self.assertEqual(200, response.status_code)
    self.assertTemplateUsed(response, self.template_success)

    results = response.context['results']
    logger.info(results)

  def test_org_fields(self):
    """ Verify that org fields can be fetched

    Setup:
      No filters selected
      All fields selected
      Format = browse

    Asserts:
      Basic success: 200 status, correct template
      Number of rows in results == number of organizations in db
    """

    form = OrgReportForm()
    post_dict = self.fill_report_form(form, fields=True)
    post_dict['run-organization'] = ''

    response = self.client.post(self.url, post_dict)

    self.assertEqual(response.status_code, 200)
    self.assertTemplateUsed(response, self.template_success)

    results = response.context['results']
    self.assertEqual(len(results), models.Organization.objects.count())

  def test_org_fields_csv(self):
    """ Verify that org fields can be fetched in csv format

    Setup:
      No filters selected
      All fields selected
      Format = browse

    Asserts:
      Basic success: able to iterate through response with reader
      Number of rows in results matches number of orgs in db

    """

    form = OrgReportForm()
    post_dict = self.fill_report_form(form, fields=True, fmt='csv')
    post_dict['run-organization'] = ''

    response = self.client.post(self.url, post_dict)

    reader = unicodecsv.reader(response, encoding = 'utf8')
    row_count = sum(1 for row in reader)
    self.assertEqual(row_count-2, models.Organization.objects.count())

  def test_org_filters_all(self):
    """ Verify that all filters can be selected in org report without error

    Setup:
      All fields
      All filters
      Format = browse

    Asserts:
      Basic success: 200 status, correct template
    """

    form = OrgReportForm()
    post_dict = self.fill_report_form(form, fields=True, filters=True)
    post_dict['run-organization'] = ''

    response = self.client.post(self.url, post_dict)

    self.assertEqual(200, response.status_code)
    self.assertTemplateUsed(response, self.template_success)

    results = response.context['results']
    self.assertEqual(0, len(results))


@override_settings(MIDDLEWARE_CLASSES = TEST_MIDDLEWARE)
class AdminInlines(BaseGrantTestCase):
  """ Verify basic display of related inlines for grants objects in admin """

  fixtures = LIVE_FIXTURES

  def setUp(self): #don't super, can't set cycle dates with this fixture
    self.logInAdmin()

  def test_organization(self):
    """ Verify that related inlines show existing objs

    Setup:
      Log in as admin, go to org #
      Orgs 41, 154, 156 have application, draft, gp grant

    Asserts:
      Application inline
    """

    organization = models.Organization.objects.get(pk=41)

    app = organization.grantapplication_set.all()[0]

    response = self.client.get('/admin/grants/organization/41/')

    self.assertContains(response, app.grant_cycle.title)
    self.assertContains(response, app.pre_screening_status)

  def test_givingproject(self):
    """ Verify that assigned grant applications (projectapps) are shown as inlines

    Setup:
      Find a GP that has projectapps

    Asserts:
      Displays one of the assigned apps
    """

    apps = models.ProjectApp.objects.filter(giving_project_id=19)

    response = self.client.get('/admin/fund/givingproject/19/')

    self.assertContains(response, 'selected="selected">' + str(apps[0].application))

  def test_application(self):
    """ Verify that gp assignment and awards are shown on application page

    Setup:
      Use application with GP assignment. App 274, Papp 3
    """

    papp = models.ProjectApp.objects.get(pk=3)

    response = self.client.get('/admin/grants/grantapplication/274/')

    self.assertContains(response, papp.giving_project.title)
    self.assertContains(response, papp.screening_status)


@override_settings(MIDDLEWARE_CLASSES = TEST_MIDDLEWARE)
class AdminRevert(BaseGrantTestCase):

  def setUp(self):
    super(AdminRevert, self).setUp(login='admin')

  def test_load_revert(self):

    response = self.client.get('/admin/grants/grantapplication/1/revert')

    self.assertEqual(200, response.status_code)
    self.assertContains(response, 'Are you sure you want to revert this application into a draft?')

  def test_revert_app(self):
    """ scenario: revert submitted app pk1
        verify:
          draft created
          app gone
          draft fields match app (incl cycle, timeline) """

    self.assertEqual(0, models.DraftGrantApplication.objects.filter(organization_id=2, grant_cycle_id=1).count())
    app = models.GrantApplication.objects.get(organization_id=2, grant_cycle_id=1)

    response = self.client.post('/admin/grants/grantapplication/1/revert')

    self.assertEqual(1, models.DraftGrantApplication.objects.filter(organization_id=2, grant_cycle_id=1).count())
    draft = models.DraftGrantApplication.objects.get(organization_id=2, grant_cycle_id=1)
    assert_app_matches_draft(self, draft, app, False)

@unittest.skip('Incomplete')
@override_settings(MIDDLEWARE_CLASSES = TEST_MIDDLEWARE)
class AdminRollover(BaseGrantTestCase):

  def setUp(self):
    super(AdminRollover, self).setUp(login='admin')


