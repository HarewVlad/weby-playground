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
import { Kanban, List, Plus, MoreHorizontal, GripVertical, Bell, User, Search, Filter, Settings, ChevronLeft, ChevronRight, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from "@/components/ui/card";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
  DragOverlay,
  DragStartEvent
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
  horizontalListSortingStrategy,
  useSortable
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { useRouter } from "next/navigation";

// SortableItem component implementation
function SortableItem({ id, children }: { id: string | number; children: React.ReactNode }) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div ref={setNodeRef} style={style} {...attributes} {...listeners}>
      {children}
    </div>
  );
}

// SortableList component for the columns
function SortableList({ id, children }: { id: string | number; children: React.ReactNode }) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
  } = useSortable({ id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  return (
    <div ref={setNodeRef} style={style} {...attributes}>
      {children}
    </div>
  );
}

export default function MangaFlow() {
  const router = useRouter();
  const [boards] = useState([
    { id: 1, name: "Personal Reading List", color: "bg-blue-500" },
    { id: 2, name: "Manga Club Picks", color: "bg-green-500" },
    { id: 3, name: "Creative Projects", color: "bg-purple-500" },
    { id: 4, name: "Wishlist", color: "bg-yellow-500" }
  ]);

  const [currentBoard, setCurrentBoard] = useState(boards[0]);
  const [activeCard, setActiveCard] = useState<any>(null);
  const [activeList, setActiveList] = useState<any>(null);

  const [lists, setLists] = useState([
    { id: 1, name: "To Read", boardId: 1 },
    { id: 2, name: "Reading", boardId: 1 },
    { id: 3, name: "Completed", boardId: 1 },
    { id: 4, name: "On Hold", boardId: 1 }
  ]);

  const [cards, setCards] = useState([
    { 
      id: 1, 
      listId: 1, 
      title: "Chainsaw Man", 
      cover: "https://mangaplus.shueisha.co.jp/drm/title/100140/100140_1db6b9f8b3e8e1f04e1e5b4d9c4d6e3a_1.jpg",
      progress: 0,
      chapters: 97,
      currentPage: 1,
      totalPages: 200
    },
    { 
      id: 2, 
      listId: 1, 
      title: "Jujutsu Kaisen", 
      cover: "https://mangaplus.shueisha.co.jp/drm/title/100150/100150_1db6b9f8b3e8e1f04e1e5b4d9c4d6e3a_1.jpg",
      progress: 0,
      chapters: 200,
      currentPage: 1,
      totalPages: 200
    },
    { 
      id: 3, 
      listId: 2, 
      title: "One Piece", 
      cover: "https://mangaplus.shueisha.co.jp/drm/title/100020/100020_1db6b9f8b3e8e1f04e1e5b4d9c4d6e3a_1.jpg",
      progress: 45,
      chapters: 1080,
      currentPage: 450,
      totalPages: 1080
    },
    { 
      id: 4, 
      listId: 3, 
      title: "Berserk", 
      cover: "https://mangaplus.shueisha.co.jp/drm/title/100040/100040_1db6b9f8b3e8e1f04e1e5b4d9c4d6e3a_1.jpg",
      progress: 100,
      chapters: 364,
      currentPage: 364,
      totalPages: 364
    }
  ]);

  // State for adding new items
  const [newListName, setNewListName] = useState("");
  const [showNewListInput, setShowNewListInput] = useState(false);
  const [newMangaTitle, setNewMangaTitle] = useState("");
  const [showNewMangaInput, setShowNewMangaInput] = useState<number | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 10,
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  function handleDragStart(event: DragStartEvent) {
    if (event.active.data.current?.type === "card") {
      setActiveCard(cards.find(card => card.id === event.active.id));
    } else if (event.active.data.current?.type === "list") {
      setActiveList(lists.find(list => list.id === event.active.id));
    }
  }

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    
    if (!over) return;

    // Handle card sorting within same list
    if (active.id !== over.id && active.data.current?.type === "card" && over.data.current?.type === "card") {
      const activeListId = active.data.current?.listId;
      const overListId = over.data.current?.listId;

      // If moving within same list
      if (activeListId === overListId) {
        setCards((items) => {
          const oldIndex = items.findIndex(item => item.id === active.id);
          const newIndex = items.findIndex(item => item.id === over.id);
          return arrayMove(items, oldIndex, newIndex);
        });
      } 
      // If moving to different list
      else {
        setCards((items) => {
          const activeIndex = items.findIndex(item => item.id === active.id);
          const updatedItems = [...items];
          updatedItems[activeIndex] = {
            ...updatedItems[activeIndex],
            listId: overListId
          };
          return updatedItems;
        });
      }
    }

    // Handle list sorting
    if (active.id !== over.id && active.data.current?.type === "list" && over.data.current?.type === "list") {
      setLists((items) => {
        const oldIndex = items.findIndex(item => item.id === active.id);
        const newIndex = items.findIndex(item => item.id === over.id);
        return arrayMove(items, oldIndex, newIndex);
      });
    }

    setActiveCard(null);
    setActiveList(null);
  }

  function handleDragCancel() {
    setActiveCard(null);
    setActiveList(null);
  }

  function handleCardClick(cardId: number) {
    router.push(`/manga/${cardId}`);
  }

  function updatePage(cardId: number, increment: boolean) {
    setCards(prevCards => 
      prevCards.map(card => 
        card.id === cardId 
          ? { 
              ...card, 
              currentPage: Math.max(1, Math.min(card.totalPages, increment ? card.currentPage + 1 : card.currentPage - 1)),
              progress: Math.round((Math.max(1, Math.min(card.totalPages, increment ? card.currentPage + 1 : card.currentPage - 1)) / card.totalPages) * 100)
            } 
          : card
      )
    );
  }

  function addNewList() {
    if (!newListName.trim()) return;
    
    const newList = {
      id: Date.now(),
      name: newListName,
      boardId: currentBoard.id
    };

    setLists([...lists, newList]);
    setNewListName("");
    setShowNewListInput(false);
  }

  function addNewManga(listId: number) {
    if (!newMangaTitle.trim()) return;
    
    const newManga = {
      id: Date.now(),
      listId,
      title: newMangaTitle,
      cover: "",
      progress: 0,
      chapters: 0,
      currentPage: 1,
      totalPages: 200
    };

    setCards([...cards, newManga]);
    setNewMangaTitle("");
    setShowNewMangaInput(null);
  }

  function removeManga(cardId: number, e: React.MouseEvent) {
    e.stopPropagation();
    setCards(cards.filter(card => card.id !== cardId));
  }

  return (
    <div className="min-h-screen bg-slate-100">
      {/* Header */}
      <header className="sticky top-0 z-50 w-full border-b bg-white/95 backdrop-blur">
        <div className="container flex h-14 items-center justify-between px-4">
          <div className="flex items-center space-x-4">
            <div className="flex items-center">
              <Kanban className="h-5 w-5 mr-2 text-blue-600" />
              <span className="font-bold">MangaFlow</span>
            </div>
            
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="sm" className="flex items-center">
                  {currentBoard.name}
                  <MoreHorizontal className="ml-1 h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent>
                {boards.map(board => (
                  <DropdownMenuItem 
                    key={board.id} 
                    onClick={() => setCurrentBoard(board)}
                    className="flex items-center"
                  >
                    <div className={`w-3 h-3 rounded-full mr-2 ${board.color}`}></div>
                    {board.name}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>
          </div>

          <div className="flex items-center space-x-4">
            <div className="relative">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search..."
                className="pl-8 w-[150px] md:w-[200px] lg:w-[300px]"
              />
            </div>
            <Button variant="ghost" size="icon">
              <Bell className="h-5 w-5" />
            </Button>
            <Avatar className="h-8 w-8">
              <AvatarFallback>U</AvatarFallback>
            </Avatar>
          </div>
        </div>
      </header>

      <main className="container px-4 py-6">
        {/* Board Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center">
            <div className={`w-3 h-3 rounded-full mr-2 ${currentBoard.color}`}></div>
            <h1 className="text-xl font-bold">{currentBoard.name}</h1>
          </div>
          <div className="flex items-center space-x-2">
            <Button variant="outline" size="sm">
              <Filter className="mr-2 h-4 w-4" />
              Filter
            </Button>
            <Button variant="outline" size="sm">
              <Settings className="mr-2 h-4 w-4" />
              Settings
            </Button>
          </div>
        </div>

        {/* Board Content */}
        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
          onDragCancel={handleDragCancel}
        >
          <div className="flex items-start overflow-x-auto pb-4">
            <SortableContext 
              items={lists.filter(list => list.boardId === currentBoard.id).map(list => list.id)} 
              strategy={horizontalListSortingStrategy}
            >
              {lists.filter(list => list.boardId === currentBoard.id).map(list => (
                <SortableList key={list.id} id={list.id}>
                  <div className="w-72 min-w-[288px] mr-4" data-list-id={list.id}>
                    <div className="bg-white rounded-lg shadow">
                      {/* List Header */}
                      <div className="px-4 py-2 border-b flex items-center justify-between">
                        <div className="flex items-center">
                          <List className="h-4 w-4 mr-2 text-muted-foreground" />
                          <h3 className="font-medium">{list.name}</h3>
                        </div>
                        <Button variant="ghost" size="icon" className="h-6 w-6">
                          <MoreHorizontal className="h-4 w-4" />
                        </Button>
                      </div>

                      {/* Cards */}
                      <div className="p-2 space-y-2">
                        <SortableContext 
                          items={cards.filter(card => card.listId === list.id).map(card => card.id)} 
                          strategy={verticalListSortingStrategy}
                        >
                          {cards.filter(card => card.listId === list.id).map(card => (
                            <SortableItem key={card.id} id={card.id}>
                              <Card 
                                className="group cursor-pointer hover:bg-slate-50 relative"
                                onClick={() => handleCardClick(card.id)}
                              >
                                <Button 
                                  variant="ghost" 
                                  size="icon" 
                                  className="absolute top-1 right-1 h-6 w-6 opacity-0 group-hover:opacity-100"
                                  onClick={(e) => removeManga(card.id, e)}
                                >
                                  <X className="h-3 w-3" />
                                </Button>
                                <CardHeader className="p-3">
                                  <div className="aspect-[3/4] bg-muted rounded mb-2 overflow-hidden h-32">
                                    {card.cover && (
                                      <div className="w-full h-full bg-cover bg-center" 
                                          style={{ backgroundImage: `url(${card.cover})` }} />
                                    )}
                                  </div>
                                  <CardTitle className="text-base">{card.title}</CardTitle>
                                </CardHeader>
                                <CardContent className="p-3 pt-0">
                                  <div className="flex items-center justify-between text-sm text-muted-foreground">
                                    <span>Page {card.currentPage}/{card.totalPages}</span>
                                    <GripVertical className="h-4 w-4 opacity-0 group-hover:opacity-100" />
                                  </div>
                                  <div className="w-full bg-gray-200 rounded-full h-1.5 mt-2">
                                    <div 
                                      className="bg-blue-600 h-1.5 rounded-full" 
                                      style={{ width: `${(card.currentPage / card.totalPages) * 100}%` }}
                                    />
                                  </div>
                                </CardContent>
                                <CardFooter className="p-3 pt-0 flex justify-between">
                                  <Button 
                                    variant="ghost" 
                                    size="sm" 
                                    className="h-8 w-8 p-0"
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      updatePage(card.id, false);
                                    }}
                                    disabled={card.currentPage <= 1}
                                  >
                                    <ChevronLeft className="h-4 w-4" />
                                  </Button>
                                  <Button 
                                    variant="ghost" 
                                    size="sm" 
                                    className="h-8 w-8 p-0"
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      updatePage(card.id, true);
                                    }}
                                    disabled={card.currentPage >= card.totalPages}
                                  >
                                    <ChevronRight className="h-4 w-4" />
                                  </Button>
                                </CardFooter>
                              </Card>
                            </SortableItem>
                          ))}
                        </SortableContext>

                        {showNewMangaInput === list.id ? (
                          <div className="space-y-2">
                            <Input
                              placeholder="Enter manga title"
                              value={newMangaTitle}
                              onChange={(e) => setNewMangaTitle(e.target.value)}
                              autoFocus
                            />
                            <div className="flex space-x-2">
                              <Button 
                                size="sm" 
                                onClick={() => addNewManga(list.id)}
                                disabled={!newMangaTitle.trim()}
                              >
                                Add Manga
                              </Button>
                              <Button 
                                variant="outline" 
                                size="sm" 
                                onClick={() => {
                                  setNewMangaTitle("");
                                  setShowNewMangaInput(null);
                                }}
                              >
                                Cancel
                              </Button>
                            </div>
                          </div>
                        ) : (
                          <Button 
                            variant="ghost" 
                            size="sm" 
                            className="w-full justify-start text-muted-foreground"
                            onClick={() => setShowNewMangaInput(list.id)}
                          >
                            <Plus className="h-4 w-4 mr-1" />
                            Add a card
                          </Button>
                        )}
                      </div>
                    </div>
                  </div>
                </SortableList>
              ))}
            </SortableContext>

            {/* Add new list */}
            <div className="w-72 min-w-[288px]">
              {showNewListInput ? (
                <div className="bg-white rounded-lg shadow p-4 space-y-2">
                  <Input
                    placeholder="Enter list name"
                    value={newListName}
                    onChange={(e) => setNewListName(e.target.value)}
                    autoFocus
                  />
                  <div className="flex space-x-2">
                    <Button 
                      size="sm" 
                      onClick={addNewList}
                      disabled={!newListName.trim()}
                    >
                      Add List
                    </Button>
                    <Button 
                      variant="outline" 
                      size="sm" 
                      onClick={() => {
                        setNewListName("");
                        setShowNewListInput(false);
                      }}
                    >
                      Cancel
                    </Button>
                  </div>
                </div>
              ) : (
                <Button 
                  variant="ghost" 
                  className="w-full justify-start text-muted-foreground bg-white/50 hover:bg-white/70"
                  onClick={() => setShowNewListInput(true)}
                >
                  <Plus className="h-4 w-4 mr-1" />
                  Add another list
                </Button>
              )}
            </div>
          </div>
          
          <DragOverlay>
            {activeCard ? (
              <Card className="shadow-lg w-64">
                <CardHeader className="p-3">
                  <div className="aspect-[3/4] bg-muted rounded mb-2 overflow-hidden h-32">
                    {activeCard.cover && (
                      <div className="w-full h-full bg-cover bg-center" 
                          style={{ backgroundImage: `url(${activeCard.cover})` }} />
                    )}
                  </div>
                  <CardTitle className="text-base">{activeCard.title}</CardTitle>
                </CardHeader>
                <CardContent className="p-3 pt-0">
                  <div className="flex items-center justify-between text-sm text-muted-foreground">
                    <span>Page {activeCard.currentPage}/{activeCard.totalPages}</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-1.5 mt-2">
                    <div 
                      className="bg-blue-600 h-1.5 rounded-full" 
                      style={{ width: `${(activeCard.currentPage / activeCard.totalPages) * 100}%` }}
                    />
                  </div>
                </CardContent>
              </Card>
            ) : null}

            {activeList ? (
              <div className="w-72 min-w-[288px] mr-4">
                <div className="bg-white rounded-lg shadow opacity-80">
                  <div className="px-4 py-2 border-b flex items-center justify-between">
                    <div className="flex items-center">
                      <List className="h-4 w-4 mr-2 text-muted-foreground" />
                      <h3 className="font-medium">{activeList.name}</h3>
                    </div>
                  </div>
                  <div className="p-2 space-y-2">
                    {cards.filter(card => card.listId === activeList.id).slice(0, 3).map(card => (
                      <div key={card.id} className="h-16 bg-gray-100 rounded"></div>
                    ))}
                    {cards.filter(card => card.listId === activeList.id).length > 3 && (
                      <div className="text-center text-sm text-muted-foreground">
                        +{cards.filter(card => card.listId === activeList.id).length - 3} more
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ) : null}
          </DragOverlay>
        </DndContext>
      </main>
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
