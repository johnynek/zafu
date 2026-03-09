-- Rewrite relative markdown links to html during pandoc conversion.
-- Keeps absolute URLs and root-relative paths unchanged.
function Link(el)
  local target = el.target

  if target:match("^[a-zA-Z][a-zA-Z0-9+%.%-]*:") then
    return nil
  end
  if target:match("^/") then
    return nil
  end

  local base, suffix = target:match("^([^?#]+)(.*)$")
  if base == nil then
    return nil
  end

  if base:match("%.md$") then
    el.target = base:gsub("%.md$", ".html") .. suffix
    return el
  end

  return nil
end
