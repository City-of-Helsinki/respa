Resource accessibility data
===========================

In order to not replicate the complete Accessibility API, Respa stores an accessibility summary for each Resource using the Accessibility API.

This accessibility data can be used for querying Resources based on how accessible they are.

From the Accessibility API a list of Viewpoints is imported. These can be for example:

```
"I am a wheelchair user",
"I am a wheelchair user - arrive by my car",
"I am a wheelchair user - arrive with pick-up and drop-off traffic",
"I have reduced mobility, but I walk",
"I have reduced mobility, but I walk - arrive by my car",
"I have reduced mobility, but I walk - arrive with pick-up and drop-off traffic",
"I am a rollator user",
"I am a rollator user - arrive by my car",
"I am a rollator user - arrive with pick-up and drop-off traffic",
"I am a stroller pusher",
"I am visually impaired",
"I am visually impaired - arrive with pick-up and drop-off traffic",
"I use a hearing aid"
```

Each of these Viewpoints have a Value, or level of accessibility, represented as strings "red", "green" or "unknown" for inaccessible, accessible and unknown respectively. These Value types are also imported from the Accessibility API.

For example a Resource can be associated to a Viewpoint "I am a wheelchair user" and this association also points to the Value "green", meaning that the Resource is wheelchair accessible.

More detailed accessibility data can be fetched directly from the Accessibility API.
