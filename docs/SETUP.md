# Setting up and looking after the SOOTS website

This is for the teacher, or whoever owns the website. Students only need [EDITING.md](EDITING.md).

**How it works:** the website's content lives in a GitHub repository. Students edit it in
**Pages CMS** (free), and every save makes GitHub rebuild the site and publish it on
**GitHub Pages** (free). No server, no monthly bill. The only cost is the domain name.

## One-time setup

### 1. A GitHub organization the school controls

The website must not depend on any one student's account.

1. The teacher makes a free GitHub account at https://github.com/signup, ideally with the shared
   SOOTS email (sootsblues@gmail.com) or a school email that won't disappear.
2. Create a free organization at https://github.com/organizations/plan. Suggested name:
   **sootsblues**. The website address will be `https://<organization-name>.github.io/`, so
   with that name it's `https://sootsblues.github.io/`.
3. Make a second adult an **Owner** too (Settings > People), so access never depends on one person.
4. Add the student who maintains the code as a **Member**.

### 2. The repository

1. In the organization, create a new repository named exactly **`sootsblues.github.io`**, or
   `<organization-name>.github.io` if you picked a different name. That exact name makes the site
   load at the main address, which the "page not found" page depends on.
2. Make it **Public**. GitHub Pages is free for public repositories, and everything in it is
   already public on the website. Leave "Add a README" unticked.
3. The maintainer uploads the code from the project folder on their computer:

   ```bash
   cd ~/sootsblues
   git init -b main
   git add .
   git commit -m "SOOTS website with Pages CMS"
   git remote add origin https://github.com/sootsblues/sootsblues.github.io.git
   git push -u origin main
   ```

   `.gitignore` keeps the old Weebly copy, the built site and other local notes off GitHub.

### 3. Turn on GitHub Pages

1. In the repository: **Settings > Pages > Build and deployment > Source: GitHub Actions**.
2. Open the **Actions** tab, click **Build and publish the website**, then **Run workflow**. If
   the very first run (from the upload) shows a red ✗, that's because Pages wasn't on yet, so
   just run it again.
3. After about two minutes the site is live at `https://sootsblues.github.io/`.

> **Do not type a custom domain into Settings > Pages yet.** While sootsblues.org is still
> managed by Weebly/Square, it can only redirect to the github.io address. If GitHub is also told
> to send visitors to sootsblues.org, the two redirect to each other forever and the site never
> loads. Only set the custom domain after the domain has moved (see "Later" below).

### 4. Pages CMS, the editor

1. Go to https://app.pagescms.org and sign in with the teacher's GitHub account.
2. When asked, install the Pages CMS GitHub app for the **sootsblues** organization and give it
   access to the `sootsblues.github.io` repository.
3. Open the project. You should see **Home page**, **Pages**, **Special pages** and
   **Site settings and menu**. They come from the `.pages.yml` file in the repository.
4. Invite students in the project's **Collaborators** settings: add each student's email. They
   sign in with a code sent by email and don't need GitHub accounts. They can edit content and
   photos, but not settings.

## The domain (sootsblues.org)

### Now: redirect to the new site

sootsblues.org was bought through Weebly/Square, which only lets you redirect it, not point it
anywhere. When the new site looks right:

1. In the Weebly/Square domain settings, set sootsblues.org (and www) to **redirect** to
   `https://sootsblues.github.io/`.
2. Visitors to sootsblues.org now land on the new site. The address bar shows sootsblues.github.io,
   which is fine for now.

**The domain expires on December 5, 2026.** Weebly/Square bills the renewal. Check that it's set
to renew with a working card, or transfer it before then (below).

### Later: move the domain so it shows as sootsblues.org

To have the address bar say www.sootsblues.org, move the domain to a registrar that lets you
change DNS settings. For example, Cloudflare Registrar is about $11 a year (it also needs the
domain's DNS set up in Cloudflare first), and Porkbun is about $12 a year.

1. In the Weebly/Square domain settings, unlock the domain and get its **transfer code**
   (also called an authorization or EPP code).
2. At the new registrar, start a transfer and enter the code. Approve the confirmation email. It
   takes up to about a week and adds a year to the registration. Don't renew at Weebly/Square right
   before transferring, or the year you paid for may be lost.
3. In the new registrar's DNS settings, add:
   - four **A** records for `sootsblues.org`: `185.199.108.153`, `185.199.109.153`,
     `185.199.110.153`, `185.199.111.153`
   - a **CNAME** record for `www` pointing to `sootsblues.github.io`
   - any email (**MX**) records the old setup had, if anyone uses an @sootsblues.org address.
     Check before moving.
4. Only now: GitHub repository **Settings > Pages > Custom domain**: enter `www.sootsblues.org`
   and save. When GitHub's check passes, tick **Enforce HTTPS**.

## Every school year

- [ ] Invite this year's student editors in Pages CMS (Collaborators), and remove last year's graduates.
- [ ] Make sure at least two adults are Owners of the GitHub organization.
- [ ] Check the domain renewal date (early December).
- [ ] Look at the repository's **Actions** tab. Green ✓ means recent saves went live.
- [ ] Download a backup copy: repository page > **Code** > **Download ZIP**.

## Undoing a mistake

Every save is recorded on GitHub. To bring back an older version of a page, open the file on
GitHub (for example `content/pages/cake-bake.json`), click **History**, find the version you
want, and restore it, or ask the maintainer to. Photos that were deleted can be brought back the
same way from `content/photos`.

## Limits worth knowing

GitHub Pages allows a 1 GB site (this one is about 130 MB) and files up to 100 MB. Put large
videos on YouTube and embed them instead.
