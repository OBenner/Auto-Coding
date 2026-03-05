/**
 * Search input for code search
 */

import { Search } from 'lucide-react';
import { Input } from '../ui/input';

interface SearchBarProps {
  searchQuery: string;
  onSearchChange: (query: string) => void;
  placeholder?: string;
}

export function SearchBar({
  searchQuery,
  onSearchChange,
  placeholder = 'Search code...'
}: SearchBarProps) {
  return (
    <div className="relative">
      <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
      <Input
        placeholder={placeholder}
        value={searchQuery}
        onChange={(e: React.ChangeEvent<HTMLInputElement>) => onSearchChange(e.target.value)}
        className="pl-9"
      />
    </div>
  );
}
