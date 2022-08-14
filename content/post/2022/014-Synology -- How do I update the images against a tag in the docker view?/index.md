---
title: "Synology    How Do I Update the Images Against a Tag in the Docker View?"
date: 2022-08-14T15:24:00+10:00
draft: false
tags: ["annoyance"]
categories: ["synology"]
---

![img.png](img.png)

So when you use docker with Synology it has a rather
nice UI.. However it seems to be lacking things.

Such as redownloading the images for any given tag
as the SHAs don't change but the tags do! -_-

Saying that; this addition is nice:
![](ksnip_20220814-152207.png)

-- 

Turns out adding itself over itself doesn't work.

And you can't add the update by a different tag name
and switch the tag on an "off" container.. So I had 
to export:
![img_1.png](img_1.png)

![img_2.png](img_2.png)

Manually modify then reupload

![img_3.png](img_3.png)

That worked.

Side note; this message comes up regardless of the 
containers actual status.. Rather annoying.

![img_4.png](img_4.png)
