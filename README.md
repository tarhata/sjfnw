#### [Installation and setup guide](https://github.com/aisapatino/sjfnw/blob/master/SETUP.md)

#### Code

- **2 space indents** Python is space/indent sensitive and varying indents will throw errors.
- Generally follow google's [Python style guide](http://google-styleguide.googlecode.com/svn/trunk/pyguide.html) (a work in progress in the current code)

#### Issue tracking

- Issues are filed in github: [sjfnw issues](https://github.com/aisapatino/sjfnw/issues)
- The goal setup is something like
  - Milestones with no due date for broad sorting ('1 top priority', '2 nice to have', etc)
  - Sprints have their own milestones with a due date. Issues are pulled from the highest priority bucket milestone.
  - Sprint milestones are closed at the end of the sprint and unfinished issues are moved into the next sprint.
- Always search issues before creating a new one to make sure it hasn't already been filed.

#### Git

- `master` represents code that is in production.
- `develop` is the main integration branch.
- Short-lived branches should be created and then merged into develop.
- Generally aim for small commits with descriptive summaries.
- [Link issues](https://help.github.com/articles/closing-issues-via-commit-messages/) in your commit descriptions when applicable.

See [this post](http://nvie.com/posts/a-successful-git-branching-model/) for more details on the general git branching model we're going for.

