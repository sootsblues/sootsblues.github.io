# How to edit the SOOTS website

You don't need to know any code. You edit the site in **Pages CMS**, a free website editor,
and the site updates itself a couple of minutes after you save.

## 1. Get access

1. Go to **https://app.pagescms.org** and sign in with that email address. Pages CMS emails you a
   code to type in. You don't need a GitHub account.
2. Open the SOOTS website project (https://sootsblues.github.io).

## 2. Find what you want to change

The editor's menu has four parts:

| In the menu | Material |
|---|---|
| **Home page** | The slideshow, introduction, Showcase cards, timeline, musicians list, poster strip, partner logos |
| **Pages** | Ordinary pages: About, Cake Bake, Art Farm, Fat Tuesday, the episode pages, Treasured Artists, Photo Gallery… |
| **Special pages** | Pages with their own layout: Events (the ticket cards), Soil to Soul Series (the episodes), Folk Projects (the years), Archive (posters), Contact Us, Donations, Local Support, Social, In the Field, 2026: The Macon Farm, Prarthana's poem, Episode 3: Fountain |
| **Site settings and menu** | The top menu, the footer, the email address, social media links |

## 3. Edit a page

Most pages are a list of **Page sections**, from top to bottom: Text, Heading, Photo, Photo
gallery, Button, YouTube or SoundCloud, Audio player, Video file, Side-by-side columns, and
Contact form.

- **Change text:** open a Text section and type. The toolbar has bold, italics, links and lists.
- **Add a section:** use the add button under Page sections and pick the kind you want.
- **Move or remove a section:** use the controls on that section.
- When you're done, click **Save**.

## 4. Photos and names

Every photo has a **Caption** box. **Please write who is in the photo**, for example
"Sister Lena Mae Perry and Phil Cook at Raleigh Charter, April 2019". Names help visitors and the
students who come after you.

- **One photo:** add a **Photo** section, click the image box, and upload the picture.
- **Many photos:** add a **Photo gallery** section, then add each photo with its caption.
  Galleries with 4 or more photos are shown full width under the text.
- **Before uploading:** keep each photo under about 5 MB. Phone photos are fine. File names with
  spaces are cleaned up automatically.

## 5. Videos and audio

- **YouTube video or SoundCloud track:** add a **YouTube or SoundCloud** section and paste its
  address. This is the best way to share videos.
- **Audio file (MP3):** add an **Audio player** section and upload the file.
- Keep audio and video files under 25 MB. Put bigger videos on the SOOTS YouTube channel instead.

## 6. Add a new page

1. In **Pages**, add a new page and give it a title. Use only lowercase letters, numbers
   and dashes.
2. Add sections, then **Save**.
3. To put it in the menu, go to **Site settings and menu** > **Menu**, open the right menu item,
   and add a **Dropdown link**. Type the text and the link (for example `fat-tuesday-2027.html`).

## 7. Things to update each year

- **Cake Bake page:** the date in the text and in the "At a glance" box, and new photos with names.
- **Events page:** the ticket cards (Special pages > Events page).
- **Folk Projects page:** add the new year at the top of "Projects by year".
- **Home page:** add a year to the timeline for anything big.
- **Footer:** the © year (Site settings and menu > Footer).

## 8. After you save

The site rebuilds itself, and the change is live a couple of minutes later. Refresh the page to
see it. On a phone, close and reopen the tab if it still looks old.

### If the site doesn't update

Saving can't break the live site. If something goes wrong, the previous version stays online.
To see what happened, open the project on GitHub and clicks the **Actions** tab. 
A red ✗ means the build stopped, and the log says why in plain English. For example, 
a photo was deleted but a page still uses it. Fix that in Pages CMS and save again.

## 9. Please don't

- Don't paste text from Google Docs or Word with its formatting. Use your browser's
  "Paste and Match Style" or "Paste as plain text" (in the right-click menu), then format it in the editor.
- Don't delete photos from the media library unless you're sure no page uses them.

## The other files

The **website-code** folder, **.github** and **.pages.yml** run the website. You never need to open
them: everything is edited in Pages CMS.
