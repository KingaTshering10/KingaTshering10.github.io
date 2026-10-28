module.exports = function (eleventyConfig) {
  // Copy static assets and the CMS admin straight through to the build output.
  eleventyConfig.addPassthroughCopy({ "src/assets": "assets" });
  eleventyConfig.addPassthroughCopy({ "src/admin": "admin" });

  // Human-friendly date, e.g. "20 October 2026".
  eleventyConfig.addFilter("dateDisplay", (value) =>
    new Date(value).toLocaleDateString("en-GB", {
      year: "numeric",
      month: "long",
      day: "numeric",
    })
  );

  // Newest-first ordering for the News feed.
  eleventyConfig.addCollection("newsRecent", (api) =>
    api.getFilteredByTag("news").reverse()
  );

  return {
    dir: {
      input: "src",
      includes: "_includes",
      data: "_data",
      output: "_site",
    },
    markdownTemplateEngine: "njk",
    htmlTemplateEngine: "njk",
  };
};
