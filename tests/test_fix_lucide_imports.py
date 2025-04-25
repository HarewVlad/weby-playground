import re
import textwrap
import os
import sys

# --- Add parent directory to sys.path ---
# Get the directory of the current script (tests/)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Get the parent directory (web-creator/)
PARENT_DIR = os.path.dirname(SCRIPT_DIR)
# Add the parent directory to the start of the Python module search path
sys.path.insert(0, PARENT_DIR)
# --- End of path modification ---

from utils import load_known_icons, fix_lucide_imports_filtered

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ICON_LIST_PATH = os.path.join(SCRIPT_DIR, "..", "lucide_icons_list.json")

react_code = textwrap.dedent("""
"use client";

import * as React from "react";
import { useState } from "react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from "@/components/ui/card";
import { Sun, Moon, Bold, Italic, Underline, AlignLeft, AlignRight } from "lucide-react";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { Toggle } from "@/components/ui/toggle";

export default function EditorPage() {
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [theme, setTheme] = useState<"light" | "dark">("light");
  const [textAlign, setTextAlign] = useState("left");
  const [textFormat, setTextFormat] = useState<string[]>([]);

  const handlePublish = () => {
    alert(`Post published!\\nTitle: ${title}\\nContent: ${content}`);
  };

  const toggleTheme = () => {
    setTheme(theme === "light" ? "dark" : "light");
  };

  return (
    <div className={cn("min-h-screen", theme === "dark" ? "dark bg-gray-900" : "bg-white")}>
      {/* Header */}
      <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur px-4">
        <div className="container flex h-16 items-center justify-between">
          <h1 className="text-xl font-bold">Simple Editor</h1>
          <div className="flex items-center gap-4">
            <Toggle variant="outline" aria-label="Toggle theme" onClick={toggleTheme}>
              {theme === "light" ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />}
            </Toggle>
            <Button onClick={handlePublish}>Publish</Button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container py-8">
        <Tabs defaultValue="write" className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="write">Write</TabsTrigger>
            <TabsTrigger value="preview">Preview</TabsTrigger>
          </TabsList>

          <TabsContent value="write">
            <Card className="mt-4">
              <CardHeader>
                <CardTitle>Create New Post</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="title">Title</Label>
                  <Input
                    id="title"
                    placeholder="Enter your post title"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                  />
                </div>

                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <Label htmlFor="content">Content</Label>
                    <div className="flex gap-1">
                      <ToggleGroup type="multiple" variant="outline" value={textFormat} onValueChange={setTextFormat}>
                        <ToggleGroupItem value="bold" aria-label="Toggle bold">
                          <Bold className="h-4 w-4" />
                        </ToggleGroupItem>
                        <ToggleGroupItem value="italic" aria-label="Toggle italic">
                          <Italic className="h-4 w-4" />
                        </ToggleGroupItem>
                        <ToggleGroupItem value="underline" aria-label="Toggle underline">
                          <Underline className="h-4 w-4" />
                        </ToggleGroupItem>
                      </ToggleGroup>

                      <ToggleGroup type="single" variant="outline" value={textAlign} onValueChange={setTextAlign}>
                        <ToggleGroupItem value="left" aria-label="Left aligned">
                          <AlignLeft className="h-4 w-4" />
                        </ToggleGroupItem>
                        <ToggleGroupItem value="center" aria-label="Center aligned">
                          <AlignCenter className="h-4 w-4" /> {/* Used but not imported initially */}
                        </ToggleGroupItem>
                        <ToggleGroupItem value="right" aria-label="Right aligned">
                          <AlignRight className="h-4 w-4" />
                        </ToggleGroupItem>
                      </ToggleGroup>
                    </div>
                  </div>
                  <Textarea
                    id="content"
                    placeholder="Write your post content here..."
                    value={content}
                    onChange={(e) => setContent(e.target.value)}
                    className="min-h-[300px]"
                    style={{
                      textAlign: textAlign as React.CSSProperties['textAlign'],
                      fontWeight: textFormat.includes("bold") ? "bold" : "normal",
                      fontStyle: textFormat.includes("italic") ? "italic" : "normal",
                      textDecoration: textFormat.includes("underline") ? "underline" : "none",
                    }}
                  />
                </div>
              </CardContent>
              <CardFooter className="flex justify-end">
                <Button onClick={handlePublish}>Publish Post</Button>
              </CardFooter>
            </Card>
          </TabsContent>

          <TabsContent value="preview">
            <Card className="mt-4">
              <CardHeader>
                <CardTitle>Post Preview</CardTitle>
              </CardHeader>
              <CardContent>
                {title ? (
                  <>
                    <h2 className="text-2xl font-bold mb-4">{title}</h2>
                    <div
                      className="prose dark:prose-invert max-w-none"
                      dangerouslySetInnerHTML={{ __html: content.replace(/\\n/g, '<br />') }}
                    />
                  </>
                ) : (
                  <p className="text-muted-foreground">Nothing to preview yet. Start writing to see your content here.</p>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </main>

      {/* Footer */}
      <footer className="border-t p-4 text-center text-xs text-muted-foreground">
        © {new Date().getFullYear()} Simple Editor. All rights reserved.
      </footer>
    </div>
  );
}
""")

# --- Load the actual icons ---
KNOWN_LUCIDE_ICONS = load_known_icons(ICON_LIST_PATH)

# --- Run the fix ---
fixed_react_code_filtered = fix_lucide_imports_filtered(react_code, KNOWN_LUCIDE_ICONS)

# --- Print the results ---
print("\n--- Original Code (relevant part) ---")
# Use a pattern suitable for finding the original (likely single-line) import
original_search_pattern = (
    r'import.*?from\s*["\']lucide-react["\'];?'  # Non-greedy .*? is safer
)
original_import_line_match = re.search(
    original_search_pattern, react_code, re.MULTILINE
)  # MULTILINE helps anchor ^ if used
print(
    original_import_line_match.group(0).strip()
    if original_import_line_match
    else "Original import line not found"
)


print("\n--- Fixed Code (relevant part) ---")
# Use a pattern suitable for finding single OR multiline imports, NEEDING DOTALL for multiline
fixed_search_pattern = r'import.*?from\s*["\']lucide-react["\'];?'  # Non-greedy .*?
fixed_import_line_match = re.search(
    fixed_search_pattern,
    fixed_react_code_filtered,
    re.MULTILINE | re.DOTALL,  # Add re.DOTALL here!
)
print(
    fixed_import_line_match.group(0).strip()
    if fixed_import_line_match
    else "Fixed import line not found"
)
