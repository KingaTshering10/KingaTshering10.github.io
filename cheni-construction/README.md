# Cheni Construction Private Limited — website

A fast, low-maintenance website for Cheni Construction Private Limited.

- **No database, no server.** It's a static site: pages are built from simple
  files and served as plain HTML. Free to host, nothing to maintain.
- **News & Careers** are easy to update — either through a web admin panel
  (recommended for non-technical staff) or by editing text files.
- Built with [Eleventy](https://www.11ty.dev/) (a static site generator).

---

## Run it locally

```bash
npm install      # one time
npm start        # dev server at http://localhost:8080
npm run build    # production build into _site/
```

## Project layout

```
src/
  _data/site.json      ← company name, phone, email, address, menu
  index.njk            ← home page
  about.md             ← About page text
  services.njk         ← Services
  projects.njk         ← Projects (swap placeholders for real photos)
  news.njk             ← News listing   (auto-built from src/news/*)
  careers.njk          ← Careers listing (auto-built from src/careers/*)
  contact.njk          ← Contact
  news/                ← one file per news post
  careers/             ← one file per job opening
  assets/              ← css and images (drop hero.jpg in assets/img/)
  admin/               ← the content manager (CMS)
```

## First things to edit

1. `src/_data/site.json` — replace the placeholder **phone, email, address**.
2. `src/about.md` — the company story and licence/registration details.
3. `src/projects.njk` — real projects and photos.
4. Drop a banner photo at `src/assets/img/hero.jpg`.

## Adding news / jobs by hand

- **News:** add a file in `src/news/` named `YYYY-MM-DD-title.md`:
  ```
  ---
  title: Your headline
  date: 2026-11-01
  summary: One line shown in the list.
  ---
  Your update text here.
  ```
- **Jobs:** add a file in `src/careers/` (e.g. `foreman.md`):
  ```
  ---
  title: Foreman
  location: Thimphu, Bhutan
  type: Full-time
  positions: 1
  deadline: 30 November 2026
  ---
  Job description here.
  ```
  Delete the file when the role is filled — it disappears from the site on the
  next build.

## Editing without code (the admin panel)

Once deployed, staff go to `https://YOUR-SITE/admin/`, log in with GitHub, and
add or edit News and Careers through a form. Saving commits the change and the
site rebuilds itself automatically. Config: `src/admin/config.yml`.

## Deploy (recommended: Netlify or Cloudflare Pages — free)

1. Push this project to a GitHub repo (e.g. `KingaTshering10/cheni-construction`).
2. On [Netlify](https://netlify.com) or Cloudflare Pages: **New site → import the
   repo.** Build settings are already in `netlify.toml`
   (build command `npm run build`, publish folder `_site`).
3. For the `/admin/` login, connect GitHub auth (Netlify Identity / an OAuth
   app). See the Sveltia CMS docs for the one-time setup.
4. Add a custom domain when ready.

> Applications are handled by email (the "How to apply" box on each job links to
> the company address) — no form service or backend required.
