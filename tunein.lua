-- {"name":"TuneIn Favorites","file":"","version":0,"order":2,"arguments":[]}
local service = "http://127.0.0.1:18766"
local station = mympd_arguments.station
local action = mympd_arguments.action

local function encode(value)
    return value:gsub("([^%w_.~-])", function(char)
        return string.format("%%%02X", string.byte(char))
    end)
end

local function request(method, path)
    local headers = method == "POST" and "Content-Type: application/json\r\n" or ""
    local payload = method == "POST" and "{}" or ""
    local rc, status, _, body = mympd.http_client(
        method, service .. path, headers, payload, false
    )
    if rc ~= 0 or status ~= 200 then
        return nil
    end
    return json.decode(body)
end

local function station_select(stations, name)
    local ids, names = {}, {}
    for _, item in ipairs(stations) do
        ids[#ids + 1] = item.id
        names[#names + 1] = item.name
    end
    return {
        name = name,
        type = "select",
        value = ids,
        displayValue = names,
        defaultValue = ids[1] or ""
    }
end

local function favorite_change(operation, id)
    if type(id) ~= "string" or not id:match("^s%d+$") then
        return "Select a TuneIn station"
    end
    if not request("POST", "/favorites/" .. operation .. "/" .. id) then
        return "Could not change the TuneIn favorite. Reopen favorites to check."
    end
    return operation == "add" and "Station saved to TuneIn favorites"
        or "Station removed from TuneIn favorites"
end

if mympd_arguments.add_station then
    return favorite_change("add", mympd_arguments.add_station)
end
if mympd_arguments.remove_station then
    return favorite_change("remove", mympd_arguments.remove_station)
end
local location = mympd_arguments.location
if action == "location" then
    location = "r0"
end
if location then
    if type(location) ~= "string" then
        return "Select a TuneIn location or station"
    end
    if location:match("^s%d+$") then
        return mympd.dialog("Save this TuneIn station?", {
            station_select({{id = location, name = location}}, "add_station")
        }, "TuneIn Favorites")
    end
    if not location:match("^r%d+$") then
        return "Invalid TuneIn location"
    end
    local entries = request("GET", "/locations/" .. location)
    if not entries or #entries == 0 then
        return "No TuneIn stations or locations found"
    end
    return mympd.dialog("Browse TuneIn by location", {
        station_select(entries, "location")
    }, "TuneIn Favorites")
end
if mympd_arguments.query then
    local query = mympd_arguments.query
    if type(query) ~= "string" or #query == 0 or #query > 100 then
        return "Enter a station name or call sign"
    end
    local results = request("GET", "/search?q=" .. encode(query))
    if not results or #results == 0 then
        return "No TuneIn stations found"
    end
    return mympd.dialog("Save a TuneIn station", {
        station_select(results, "add_station")
    }, "TuneIn Favorites")
end
if action == "search" then
    return mympd.dialog("Find a TuneIn station", {{
        name = "query", type = "text", value = ""
    }}, "TuneIn Favorites")
end
if action == "remove" then
    if type(station) ~= "string" or not station:match("^s%d+$") then
        return "Select a TuneIn station"
    end
    return mympd.dialog("Remove the selected TuneIn favorite?", {
        station_select({{id = station, name = station}}, "remove_station")
    }, "TuneIn Favorites")
end

if station ~= nil then
    if type(station) ~= "string" or not station:match("^s%d+$") then
        return "Invalid TuneIn station ID"
    end
    local rc, status, _, body = mympd.http_client(
        "GET", service .. "/stations/" .. station, "", "", false
    )
    if rc ~= 0 or status ~= 200 then
        return "Could not resolve the TuneIn stream"
    end
    local stream = json.decode(body)
    local uri = stream.url:gsub("#.*$", "") .. "#mympd-tunein=" .. station
        .. "&name=" .. encode(stream.name or "")
        .. "&art=" .. encode(stream.artFile or "")
    local result
    rc, result = mympd.api("MYMPD_API_QUEUE_APPEND_URIS", {
        uris = {uri},
        play = true
    })
    if rc ~= 0 then
        return result.message or "Could not start the TuneIn stream"
    end
    return "Started TuneIn station"
end

local rc, status, _, body = mympd.http_client(
    "GET", service .. "/stations", "", "", false
)
if rc ~= 0 or status ~= 200 then
    return "Could not load TuneIn favorites"
end
local stations = json.decode(body)
if type(stations) ~= "table" then
    return "Could not read TuneIn favorites"
end
return mympd.dialog("TuneIn Favorites", {
    station_select(stations, "station"),
    {
        name = "action",
        type = "select",
        value = {"play", "search", "location", "remove"},
        displayValue = {"Play selected station", "Find and save a station",
            "Browse by location", "Remove selected station"},
        defaultValue = #stations > 0 and "play" or "search"
    }
}, "TuneIn Favorites")
