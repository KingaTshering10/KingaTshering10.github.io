# frozen_string_literal: true

# AI assistant widget injector.
#
# This site is a thin al-folio starter: layouts and includes are owned by the
# `al_folio_core` gem and must not be shadowed here (the style contract fails CI
# if this repo owns `_includes`/`_layouts`). To add a site-wide floating chat
# widget without touching gem-owned files, this Jekyll plugin injects a
# self-contained widget before the closing </body> tag of every rendered HTML
# page at build time.
#
# The widget markup lives in `_plugins/ai_assistant_widget.html` (not published
# on its own) and its knowledge base in `_data/ai_profile.yml`. The profile is
# serialized to JSON and spliced into the widget, so the browser needs no extra
# fetch and there are no baseurl concerns.
#
# Requires a Jekyll build (`bundle exec jekyll build`), which the deploy workflow
# uses. It has no effect on GitHub's default (pluginless) Pages build.

require "json"

module AIAssistant
  WIDGET_PATH = File.expand_path("ai_assistant_widget.html", __dir__)
  PROFILE_TOKEN = "__AI_PROFILE_JSON__"
  MARKER = 'id="ai-assistant-root"'

  # Build the widget markup with the profile JSON spliced in. Cached per build.
  def self.widget_markup(site)
    return @markup if defined?(@markup) && @markup
    return "" unless File.exist?(WIDGET_PATH)

    template = File.read(WIDGET_PATH)
    profile = site.data["ai_profile"] || {}
    @markup = template.gsub(PROFILE_TOKEN, JSON.generate(profile))
  end

  def self.inject(doc)
    output = doc.output
    return unless output.is_a?(String)
    return unless output.include?("</body>")
    return if output.include?(MARKER) # already injected / not an HTML page twice

    widget = widget_markup(doc.site)
    return if widget.empty?

    # Insert before the last </body> so it lands inside the document body.
    idx = output.rindex("</body>")
    return unless idx

    doc.output = output[0...idx] + widget + "\n" + output[idx..-1]
  end
end

# Reset the cached markup at the start of each build so `--watch` picks up edits
# to the widget or the profile data.
Jekyll::Hooks.register :site, :pre_render do |_site|
  AIAssistant.remove_instance_variable(:@markup) if AIAssistant.instance_variable_defined?(:@markup)
end

Jekyll::Hooks.register :pages, :post_render do |page|
  AIAssistant.inject(page)
end

Jekyll::Hooks.register :documents, :post_render do |doc|
  AIAssistant.inject(doc)
end
