# Guide to version control

There are many ways to contribute to an open source project. Since pydap is already hosted
on Github, we recommend using [Git](https://git-scm.com) for keeping track of changes and
contribute to the project. There are many online tutorials for best practices for git, so
we provide a summarized approach. We will assume that you have [GitHub](https://github.com)
account and that you are signed in.

## Using git and GitHub

Go to [pydap](https://github.com/pydap/pydap) and [fork](https://docs.github.com/en/get-started/quickstart/fork-a-repo) it. If you already have a fork, make sure your forked project is up-to-date
with the remote project. If it is not, [sync](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/syncing-a-fork) your fork.


Open your terminal. Set your GitHub username and ermail address using the following commands:

```shell
git config --global user.email "you@example.com"
git config --global user.name "Your Name"
```

Create a local clone of your fork as follows

```shell
git clone https://github.com/<your_username_here>/pydap.git
```

Move into your local clone directory and setup a remote that points to the original

```shell
cd pydap
git remote add upstream https://github.com/pydap/pydap
git fetch upstream/main
```

A great feature of git is the ability to work on branches when developing a project. A branch helps
keep track of changes while keeping a local copy of the remote, unchanged code. To start a branch to making a contribution to pydap

```shell
git checkout -b <name_of_branch>
```

You are now on a branch and can safely make changes to your local clone. To stage them to become visible
to other contributors, you need to push your branch to your forked project. To achieve that run

```shell
git push --set-upstream origin <name_of_branch>
```

You can now make changes, create commits and push them onto your forked project. To create a commit based on your local changes on your branch, run

```shell
git add .
git commit -m 'Minimal message describing changes'
```

This will create a milestone to revert back. When you are done with your changes, or want your collaborators to become aware of your work on your forked project, run

```shell
git push
```

You can go to your remote GitHub directory and find your changes.
