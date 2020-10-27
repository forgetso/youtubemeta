# youtubemeta
Download data from YouTube channels - Video titles, view counts, dates, and URLs

To get started  

`pip install youtubemeta`

Then import the module and run for the channel  

```
import youtubemeta  
metadata = youtubemeta.scrape('CHANNEL_NAME')
```

Arguments

```
--write    write to CSV
--path     specify custom path and filename for the csv
```


<p xmlns:dct="http://purl.org/dc/terms/">
  <a rel="license"
     href="http://creativecommons.org/publicdomain/zero/1.0/">
    <img src="http://i.creativecommons.org/p/zero/1.0/88x31.png" style="border-style: none;" alt="CC0" />
  </a>
  <br />
  To the extent possible under law,
  <a rel="dct:publisher"
     href="https://github.com/forgetso/youtubemeta">
    <span property="dct:title">Chris Taylor</span></a>
  has waived all copyright and related or neighboring rights to
  <span property="dct:title">youtubemeta</span>.
</p>
