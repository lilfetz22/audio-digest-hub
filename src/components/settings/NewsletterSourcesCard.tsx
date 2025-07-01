
import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Trash2 } from 'lucide-react';
import { AddSourceForm } from './AddSourceForm';

interface NewsletterSource {
  id: string;
  sender_email: string;
  custom_name: string;
}

interface NewsletterSourcesCardProps {
  sources: NewsletterSource[];
  newSource: { sender_email: string; custom_name: string };
  setNewSource: React.Dispatch<React.SetStateAction<{ sender_email: string; custom_name: string }>>;
  onAddSource: (e: React.FormEvent) => void;
  onDeleteSource: (id: string) => void;
}

export const NewsletterSourcesCard: React.FC<NewsletterSourcesCardProps> = ({
  sources,
  newSource,
  setNewSource,
  onAddSource,
  onDeleteSource,
}) => {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Newsletter Sources</CardTitle>
        <CardDescription>
          Add email addresses from newsletters you want to convert to audio
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <AddSourceForm
          newSource={newSource}
          setNewSource={setNewSource}
          onSubmit={onAddSource}
        />

        {sources.length > 0 && (
          <div className="space-y-2">
            <h4 className="font-medium">Current Sources</h4>
            {sources.map((source) => (
              <div key={source.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <div>
                  <p className="font-medium">{source.custom_name}</p>
                  <p className="text-sm text-gray-600">{source.sender_email}</p>
                </div>
                <Button
                  variant="outline"
                  size="icon"
                  onClick={() => onDeleteSource(source.id)}
                  className="text-red-600 hover:text-red-700"
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
};
