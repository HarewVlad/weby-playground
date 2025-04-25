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
import { useState, useEffect } from "react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Table, TableHeader, TableRow, TableHead, TableBody, TableCell } from "@/components/ui/table";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Shield, CreditCard, Banknote, Key, Clock, ChevronRight } from "lucide-react";


export default function HomePage() {
const [balance, setBalance] = useState(12500);
const [bondHoldings, setBondHoldings] = useState(8750);
const [reservedTithes, setReservedTithes] = useState(4200);
const [securityLevel, setSecurityLevel] = useState(87);


const transactions = [
{ id: 1, type: "deposit", amount: 1500, date: "2023-10-15", description: "Munitorum payroll" },
{ id: 2, type: "withdrawal", amount: 750, date: "2023-10-14", description: "Forge world tithe" },
{ id: 3, type: "deposit", amount: 2200, date: "2023-10-12", description: "Trade fleet proceeds" },
{ id: 4, type: "transfer", amount: 500, date: "2023-10-10", description: "Adeptus Arbites fine" },
];


useEffect(() => {
// Simulate security level fluctuation
const interval = setInterval(() => {
setSecurityLevel(prev => Math.min(100, Math.max(80, prev + (Math.random() > 0.5 ? 1 : -1))));
}, 3000);
return () => clearInterval(interval);
}, []);


return (
<div className="min-h-screen bg-gradient-to-b from-gray-900 to-gray-950 text-gray-100">
{/* Header */}
<header className="sticky top-0 z-50 w-full border-b border-gray-800 bg-gray-900/95 backdrop-blur">
<div className="container flex h-16 items-center justify-between px-4">
<div className="flex items-center space-x-2">
<div className="h-8 w-8 rounded-full bg-gradient-to-br from-yellow-600 to-red-700 flex items-center justify-center">
<div className="h-6 w-6 rounded-full border-2 border-yellow-400"></div>
</div>
<h1 className="text-xl font-bold tracking-tight">
<span className="bg-gradient-to-r from-yellow-400 to-yellow-600 bg-clip-text text-transparent">
Bank of Terra Nexus
</span>
</h1>
</div>
<nav className="hidden md:flex items-center space-x-6">
<Button variant="ghost" className="text-gray-300 hover:text-yellow-400">
Services
</Button>
<Button variant="ghost" className="text-gray-300 hover:text-yellow-400">
Investments
</Button>
<Button variant="ghost" className="text-gray-300 hover:text-yellow-400">
Security
</Button>
</nav>
<Button className="bg-yellow-600 hover:bg-yellow-700 text-gray-900">
Access Creditorium
</Button>
</div>
</header>


  {/* Hero Section */}
  <section className="relative py-20 px-4 overflow-hidden">
    <div className="absolute inset-0 bg-[url('/grid-pattern.svg')] opacity-5"></div>
    <div className="container mx-auto relative z-10">
      <div className="max-w-3xl mx-auto text-center">
        <Badge variant="outline" className="mb-4 bg-gray-800 border-yellow-600 text-yellow-400">
          By the Emperor's Will
        </Badge>
        <h2 className="text-4xl md:text-5xl font-bold mb-6">
          <span className="bg-gradient-to-r from-yellow-400 to-yellow-600 bg-clip-text text-transparent">
            Your Wealth Is Safe
          </span>
          <br />
          Under the Emperor's Vigil
        </h2>
        <p className="text-xl text-gray-300 mb-8">
          Securing the Imperium's wealth across millennia with sanctified financial instruments
          and Omnissiah-blessed encryption.
        </p>
        <div className="flex flex-col sm:flex-row justify-center gap-4">
          <Button className="bg-yellow-600 hover:bg-yellow-700 text-gray-900 px-8 py-6 text-lg">
            Access Your Creditorium
          </Button>
          <Button variant="outline" className="border-yellow-600 text-yellow-400 hover:bg-gray-800 px-8 py-6 text-lg">
            Discover Our Services
          </Button>
        </div>
      </div>
    </div>
  </section>

  {/* Features Section */}
  <section className="py-16 px-4 bg-gray-900/50 border-y border-gray-800">
    <div className="container mx-auto">
      <h3 className="text-2xl font-bold mb-12 text-center">
        Sanctified Financial Instruments
      </h3>
      <div className="grid md:grid-cols-3 gap-8">
        <Card className="border-gray-800 bg-gray-900/50 hover:bg-gray-900 transition-colors">
          <CardHeader>
            <div className="flex items-center justify-center w-12 h-12 rounded-full bg-yellow-600/20 mb-4">
              <Banknote className="w-6 h-6 text-yellow-400" />
            </div>
            <CardTitle className="text-yellow-400">Imperial Credit Accounts</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-gray-300">
              Secure your standard cred units, with holdings denominated in Terra-standard SU.
              Protected by the Adeptus Custodes-grade security protocols.
            </p>
          </CardContent>
          <CardFooter>
            <Button variant="link" className="text-yellow-400 p-0">
              Learn more <ChevronRight className="ml-1 w-4 h-4" />
            </Button>
          </CardFooter>
        </Card>

        <Card className="border-gray-800 bg-gray-900/50 hover:bg-gray-900 transition-colors">
          <CardHeader>
            <div className="flex items-center justify-center w-12 h-12 rounded-full bg-yellow-600/20 mb-4">
              <CreditCard className="w-6 h-6 text-yellow-400" />
            </div>
            <CardTitle className="text-yellow-400">Adeptus Investment Bonds</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-gray-300">
              Participate in Holy Missions—minimal risk, sanctified returns. Fund crusades,
              colonization efforts, and forge world expansions with blessed yields.
            </p>
          </CardContent>
          <CardFooter>
            <Button variant="link" className="text-yellow-400 p-0">
              Learn more <ChevronRight className="ml-1 w-4 h-4" />
            </Button>
          </CardFooter>
        </Card>

        <Card className="border-gray-800 bg-gray-900/50 hover:bg-gray-900 transition-colors">
          <CardHeader>
            <div className="flex items-center justify-center w-12 h-12 rounded-full bg-yellow-600/20 mb-4">
              <Shield className="w-6 h-6 text-yellow-400" />
            </div>
            <CardTitle className="text-yellow-400">Warp-Safe Vaults</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-gray-300">
              Our Omnissian encryption repels daemon incursions and data-warp anomalies.
              Gellar field protected storage for your most valuable assets.
            </p>
          </CardContent>
          <CardFooter>
            <Button variant="link" className="text-yellow-400 p-0">
              Learn more <ChevronRight className="ml-1 w-4 h-4" />
            </Button>
          </CardFooter>
        </Card>
      </div>
    </div>
  </section>

  {/* Dashboard Preview */}
  <section className="py-16 px-4">
    <div className="container mx-auto">
      <h3 className="text-2xl font-bold mb-8 text-center">
        Your Imperial Financial Overview
      </h3>
      
      <Tabs defaultValue="overview" className="max-w-4xl mx-auto">
        <TabsList className="grid w-full grid-cols-3 bg-gray-900 border border-gray-800">
          <TabsTrigger value="overview" className="data-[state=active]:bg-yellow-600 data-[state=active]:text-gray-900">
            Overview
          </TabsTrigger>
          <TabsTrigger value="transactions" className="data-[state=active]:bg-yellow-600 data-[state=active]:text-gray-900">
            Transactions
          </TabsTrigger>
          <TabsTrigger value="security" className="data-[state=active]:bg-yellow-600 data-[state=active]:text-gray-900">
            Security
          </TabsTrigger>
        </TabsList>
        
        <TabsContent value="overview">
          <Card className="border-gray-800 bg-gray-900/50">
            <CardHeader>
              <CardTitle>Account Summary</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                <div className="bg-gray-800/50 p-6 rounded-lg border border-gray-700">
                  <h4 className="text-sm font-medium text-gray-400 mb-2">Liquid Credits</h4>
                  <p className="text-2xl font-bold text-yellow-400">{balance.toLocaleString()} SU</p>
                </div>
                <div className="bg-gray-800/50 p-6 rounded-lg border border-gray-700">
                  <h4 className="text-sm font-medium text-gray-400 mb-2">Bond Holdings</h4>
                  <p className="text-2xl font-bold text-yellow-400">{bondHoldings.toLocaleString()} SU</p>
                </div>
                <div className="bg-gray-800/50 p-6 rounded-lg border border-gray-700">
                  <h4 className="text-sm font-medium text-gray-400 mb-2">Reserved Tithes</h4>
                  <p className="text-2xl font-bold text-yellow-400">{reservedTithes.toLocaleString()} SU</p>
                </div>
              </div>

              <h4 className="text-lg font-semibold mb-4">Recent Activity</h4>
              <Table>
                <TableHeader>
                  <TableRow className="hover:bg-transparent">
                    <TableHead>Date</TableHead>
                    <TableHead>Description</TableHead>
                    <TableHead className="text-right">Amount</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {transactions.map((tx) => (
                    <TableRow key={tx.id} className="border-gray-800 hover:bg-gray-800/30">
                      <TableCell>{tx.date}</TableCell>
                      <TableCell>{tx.description}</TableCell>
                      <TableCell className={`text-right ${tx.type === 'deposit' ? 'text-green-400' : 'text-red-400'}`}>
                        {tx.type === 'deposit' ? '+' : '-'}{tx.amount.toLocaleString()} SU
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>
        
        <TabsContent value="security">
          <Card className="border-gray-800 bg-gray-900/50">
            <CardHeader>
              <CardTitle>Security Sanctum</CardTitle>
            </CardHeader>
            <CardContent>
              <Alert className="bg-yellow-600/10 border-yellow-600/50 mb-6">
                <Shield className="h-4 w-4 text-yellow-400" />
                <AlertTitle>Security Status: Sanctified</AlertTitle>
                <AlertDescription>
                  Your account is currently under the protection of the Omnissiah's encryption.
                </AlertDescription>
              </Alert>

              <div className="mb-6">
                <div className="flex justify-between mb-2">
                  <Label>Encryption Strength</Label>
                  <span className="text-yellow-400">{securityLevel}%</span>
                </div>
                <Progress value={securityLevel} className="h-2 bg-gray-800" indicatorClassName="bg-yellow-500" />
              </div>

              <div className="space-y-4">
                <div className="flex items-center justify-between p-4 bg-gray-800/50 rounded-lg border border-gray-700">
                  <div className="flex items-center space-x-3">
                    <div className="p-2 rounded-full bg-yellow-600/20">
                      <Key className="w-5 h-5 text-yellow-400" />
                    </div>
                    <div>
                      <h4 className="font-medium">Biometric Scan</h4>
                      <p className="text-sm text-gray-400">Ember-burned iris recognition</p>
                    </div>
                  </div>
                  <Badge variant="outline" className="border-green-400 text-green-400">
                    Active
                  </Badge>
                </div>

                <div className="flex items-center justify-between p-4 bg-gray-800/50 rounded-lg border border-gray-700">
                  <div className="flex items-center space-x-3">
                    <div className="p-2 rounded-full bg-yellow-600/20">
                      <Clock className="w-5 h-5 text-yellow-400" />
                    </div>
                    <div>
                      <h4 className="font-medium">Servo-Key Generator</h4>
                      <p className="text-sm text-gray-400">Physical cog-key authentication</p>
                    </div>
                  </div>
                  <Badge variant="outline" className="border-green-400 text-green-400">
                    Active
                  </Badge>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  </section>

  {/* News Ticker */}
  <section className="py-4 px-4 bg-gray-900 border-y border-gray-800">
    <div className="container mx-auto">
      <div className="flex items-center overflow-hidden">
        <div className="flex-shrink-0 mr-8 text-yellow-400 font-medium">
          Imperial Bulletins:
        </div>
        <div className="flex-1 overflow-hidden">
          <div className="whitespace-nowrap animate-marquee">
            <span className="mx-4">Astra Militarum allocations increased by 12% in Segmentum Solar</span>
            <span className="mx-4">Ecclesiarchy grants now available for shrine world development</span>
            <span className="mx-4">New tithe schedules announced for Agri-worlds in Ultima Segmentum</span>
            <span className="mx-4">Warp storm warnings in effect - transit fees adjusted accordingly</span>
          </div>
        </div>
      </div>
    </div>
  </section>

  {/* Footer */}
  <footer className="border-t border-gray-800 py-6 px-4 text-center text-sm text-gray-500">
    <div className="container mx-auto">
      <p>© {new Date().getFullYear()} Bank of Terra Nexus. All rights reserved by Imperial decree.</p>
      <p className="mt-2">
        The Emperor protects. Your wealth is sanctified under His eternal vigilance.
      </p>
    </div>
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
